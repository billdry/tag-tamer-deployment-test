#!/usr/bin/env python3

# copyright 2020 Bill Dry
# Tag Tamer utility functions

# Return the Boto3 resource type & unit to the caller
def get_resource_type_unit(type):
    if type:
        if type == "ebs":
            resource_type = 'ebs'
            unit = 'volumes'
        elif type == "ec2":
            resource_type = 'ec2'
            unit = 'instances'
        elif type == "lambda":
            resource_type = 'lambda'
            unit = 'functions'
        elif type == "s3":
            resource_type = 's3'
            unit = 'buckets'
        elif type == 'eks_cluster':
            resource_type = 'eks'
            unit = 'clusters'
        elif type == 'eks_nodegroup':
            resource_type = 'eks'
            unit = 'nodegroups'        
        else:
            resource_type = 'ec2'
            unit = 'instances'
        return resource_type, unit
    
