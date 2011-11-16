#! /usr/bin/env python

import re
import boto
import logging

logger = logging.getLogger('cawshflow')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

EC2Pricing = {
	'm1.small'    : (0.085, 0.12), # Standard instances
	'm1.large'    : (0.34 , 0.48),
	'm1.xlarge'   : (0.68 , 0.96),
	't1.micro'    : (0.02 , 0.03), # Micro
	'm2.xlarge'   : (0.50 , 0.62), # High-Memory instances
	'm2.2xlarge'  : (1.00 , 1.24),
	'm2.4xlarge'  : (2.00 , 2.48),
	'c1.medium'   : (0.17 , 0.29), # High-CPU
	'c1.xlarge'   : (0.68 , 1.16),
	'cc1.4xlarge' : (1.30 , 1.61), # Cluster-Compute
	'cc1.8xlarge' : (2.40 , 2.97),
	'cg1.4xlarge' : (2.10 , 2.60)
}

EBSRate = 0.1 / 720
CWRate  = 3.50 / 720

def regexify(glob):
	return re.compile(glob.replace('*', '.*'), re.I)

class InstanceList(object):
	# For each of the instances, we can use the following variables:
	#	instance_type (a unicode string)
	#	tags (a dictionary)
	#	state (a unicode string)
	#	placement (a unicode string representing the AZ)
	#	key_name (a unicode string)
	#	root_device_type (e.g. instance-store)
	#	monitored (detailed monitoring enabled?)
	#	architecture (e.g. x86_64)
	#	image_id (AMI ID)
	#	groups[*].name
	#	region.name (slightly different from placement group)
	
	def __init__(self, connection, names, keyNames, sGroups, types, amiID, tags):
		self.connection = connection
		
		logger.info('Getting instance information...')
		instances = []
		for reservation in connection.get_all_instances():
			instances.extend(reservation.instances)
		logger.info('Got instance information')
		
		names    = regexify(names)
		keyNames = regexify(keyNames)
		sGroups  = regexify(sGroups)
		types    = regexify(types)
		amiID    = regexify(amiID)
		tags     = dict((key, regexify(value)) for key,value in tags.items())
		self.instances = []
		for instance in instances:
			include = True
			if not names.match(instance.tags.get('Name', '')):
				include = False
			if not keyNames.match(instance.key_name):
				include = False
			if not sum(1 for g in instance.groups if sGroups.match(g.name)):
				include = False
			if not types.match(instance.instance_type):
				include = False
			if not amiID.match(instance.image_id):
				include = False
			if instance.state != 'running':
				include = False
			for key, value in tags.items():
				if not value.match(instance.tags.get(key, '')):
					include = False
			if include:
				logger.debug('Including %s => %s' % (instance.tags.get('Name', 'empty'), instance.image_id))
				self.instances.append(instance)
	
	def associateVolumes(self):
		logger.info('Getting volume information...')
		self.volumes = dict((v.id, v) for v in self.connection.get_all_volumes())
		logger.info('Got volume information')
		
		for instance in self.instances:
			instance.ebsprice = 0
			# Go through the block device mapping
			for volume in instance.block_device_mapping.values():
				v = self.volumes.pop(volume.volume_id, None)
				if v:
					# Divide the monthly price by the number 
					# of hours in a single month
					instance.ebsprice += v.size * EBSRate
	
	def reportPrices(self):
		# Now, we should go ahead and get information on pricing
		spot_pricing = {}
		for instance in self.instances:
			# Alright, this is a spot instance, so let's either
			# get pricing from our above dictionary, or update
			# the dictionary of pricing
			if instance.spot_instance_request_id:
				pricelist = spot_pricing.get(instance.instance_type, {})
				if not pricelist:
					logger.info('Getting pricing information for %s...' % instance.instance_type)
					prices = self.connection.get_spot_price_history()
					spot_pricing[instance.instance_type] = sum(p.price for p in prices) / len(prices)
				instance.price = spot_pricing[instance.instance_type]
			else:
				instance.price = EC2Pricing[instance.instance_type][0]
			# Now, if there's monitoring, then we should add
			# that charge accordingly. This is the number of
			# hours in a single month
			instance.price += int(instance.monitored) * CWRate
		
		# Alright, we've pruned these down, and so we should
		# report stats binned by various attributes
		byKeyName = {}
		byAmiID   = {}
		byTotal   = {'instance': 0, 'ebs': 0, 'count': 0}
		byTag     = {}
		for instance in self.instances:
			byKeyName.setdefault(instance.key_name, {'instance': 0, 'ebs': 0, 'count': 0})
			byAmiID.setdefault(instance.image_id  , {'instance': 0, 'ebs': 0, 'count': 0})
			
			byKeyName[instance.key_name]['instance'] += instance.price
			byKeyName[instance.key_name]['ebs']      += instance.ebsprice
			byKeyName[instance.key_name]['count']    += 1
			byAmiID[instance.image_id]['instance']   += instance.price
			byAmiID[instance.image_id]['ebs']        += instance.ebsprice
			byAmiID[instance.image_id]['count']      += 1
			byTotal['instance'] += instance.price
			byTotal['ebs']      += instance.ebsprice
			byTotal['count']    += 1
			
			for name, value in instance.tags.items():
				if name == 'Name':
					continue
				key = '%s=>%s' % (name, value)
				byTag.setdefault(key , {'instance': 0, 'ebs': 0, 'count': 0})
				byTag[key]['instance'] += instance.price
				byTag[key]['ebs']      += instance.ebsprice
				byTag[key]['count']    += 1
		
		# Now, we've aggregated everything. Print it!
		width  = 90
		format = '%030s | %8i | %8.4f | %8.4f | %8.4f | %9.2f'
		header = '%030s | %8s | %8s | %8s | %8s | %9s'
		print '=' * width
		print header % ('Key Name', 'Count', 'Instance', 'EBS', 'Total', 'Monthly')
		print '-' * width
		for k, v in byKeyName.items():
			total = v['instance'] + v['ebs']
			print format % (k[0:30], v['count'], v['instance'], v['ebs'], total, total * 720)
		
		print '=' * width
		print header % ('AMI ID', 'Count', 'Instance', 'EBS', 'Total', 'Monthly')
		print '-' * width
		for k, v in byAmiID.items():
			total = v['instance'] + v['ebs']
			print format % (k[0:30], v['count'], v['instance'], v['ebs'], total, total * 720)
		
		print '=' * width
		print header % ('Tag=>Value', 'Count', 'Instance', 'EBS', 'Total', 'Monthly')
		print '-' * width
		for k, v in byTag.items():
			total = v['instance'] + v['ebs']
			print format % (k[0:30], v['count'], v['instance'], v['ebs'], total, total * 720)
		
		print '=' * width
		total = byTotal['instance'] + byTotal['ebs']
		print format % ('Total', byTotal['count'], byTotal['instance'], byTotal['ebs'], total, total * 720)
