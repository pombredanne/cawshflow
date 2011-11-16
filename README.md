cawshflow
=========

This is a tool designed to help you figure out how much your AWS services are 
currently costing you. It allows you to filter by all of the following attributes
matching a glob you provide:

- Instance name => e.g. "cluster-*"
- Key name => e.g. "production-key"
- Security group => e.g. "mySQL"
- Instance type => e.g. "m1.xlarge"
- AMI ID => e.g. "ami-82047ed0"
- Tags => e.g. where "Environment" is "Production"

It then looks at the EBS volumes attached to each of these machines, and then
includes the cost of that instance's EBS volume(s) in its price. It displays the
hourly instance cost, EBS cost, total cost, and the monthly cost for instances
binned as follows:

- Binned by AMI
- Binned by key name
- Binned by unique tag, value pairs

Dependencies / Installation
===========================

Dependencies:

- Python
- setuptools => For installing dependencies and this package
- boto => For communicating to AWS

Installation:

	# Download from github:
	git clone git@github.com:seomoz/cawshflow.git
	# Build / install
	cd cawshflow
	sudo python setup.py install
	# Configure ~/.boto for ease
	# Run!

Running
=======

You can specify your AWS access ID and secret keys on the command line, or else
`boto` will look in a file `~/.boto` for a file of the format:

	[Credentials]
	aws_access_key_id = ...
	aws_secret_access_key = ...

To specify these on the command line instead (if perhaps you have multiple accounts):

	cawshflow --access-id=... --secret-key=...

The remaining arguments each accept a glob which filters out instances based on
whether or not they match the glob. For example, to only list instances that are
in the `production` security group (but may also belong to other security groups):

	cawshflow --security-group='production'

Or for just instances with 'cluster-' at the beginning of their name, and using
your 'awesome-developer-key', and only the 'm1.*'-class machines:

	cawshflow --instance-name='cluster-*' --key-name='awesome-developer-key' --instance-type='m1.*'

All unknown options are considered to be tag names. So, if you wanted to only
report on instances with the tag 'Environment' set to 'Production,' and using
a particular AMI, then you would say:

	cawshflow --ami-id='...' --Environment='Production'

Price Calculation
=================

For demand instances, the calculation is based on the price published by AWS at
time of writing. Spot instance prices are calculated as the average price of that
class of machine in the default availability zone over the last two months.

EBS prices are calculated on their storage, and __DO NOT INCLUDE IO OPS__. EBS
billing is based on both of these, and the second is difficult to estimate.