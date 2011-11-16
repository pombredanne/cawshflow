#! /usr/bin/env python

try:
	from setuptools import setup
	from setuptools.extension import Extension
	extra = {
		'install_requires' : ['boto']
	}
except ImportError:
	from distutils.core import setup
	from distutils.extension import Extension
	extra = {
		'dependencies' : ['boto']
	}

setup(name       = 'cawshflow',
	version      = '0.1.0',
	description  = 'AWS Pricing Summary',
	long_description = 'Fetches information on your current AWS usage, and collects statistics based on that.',
	url          = 'http://github.com/seomoz/cawshflow',
	author       = 'Dan Lecocq',
	author_email = 'dan@seomoz.org',
	keywords     = 'AWS, cawshflow, budget, pricing',
	packages     = ['cawshflow'],
	scripts      = ['bin/cawshflow'],
	classifiers  = [
		'Programming Language :: Python',
		'Intended Audience :: Developers',
		'Operating System :: OS Independent',
		'Topic :: Internet :: WWW/HTTP'
	],
	**extra
)