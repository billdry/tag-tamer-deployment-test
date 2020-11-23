#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# Getter & setter for AWS IAM

# Import AWS module for python
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Define AWS Config class to get/set IAM Roles using Boto3
class roles:
    
    #Class constructor
    def __init__(self, region, **session_credentials):
        self.region = region
        self.session_credentials = {}
        self.session_credentials['AccessKeyId'] = session_credentials['AccessKeyId']
        self.session_credentials['SecretKey'] = session_credentials['SecretKey']
        self.session_credentials['SessionToken'] = session_credentials['SessionToken']
        this_session = boto3.session.Session(
            aws_access_key_id=self.session_credentials['AccessKeyId'],
            aws_secret_access_key=self.session_credentials['SecretKey'],
            aws_session_token=self.session_credentials['SessionToken'])
        self.iam_resource = this_session.resource('iam', region_name=self.region)
        self.dynamodb = this_session.resource('dynamodb', region_name=self.region)
        self.table = self.dynamodb.Table('tag_tamer_roles')

    #Return the list of IAM Roles for the specified path prefix
    def get_roles(self, path_prefix):
        raw_roles_inventory = self.iam_resource.roles.filter(
            PathPrefix=path_prefix
        )
        roles_inventory = list()
        for raw_role in raw_roles_inventory:
            roles_inventory.append(raw_role.role_name)

        roles_inventory.sort(key=str.lower)

        return roles_inventory

    #Get a specified role and assigned tags 
    def get_role_tags(self, role_arn):
        response = dict()
        response = self.table.get_item(
            Key={
                'role_arn': role_arn
            },
            ProjectionExpression="tags"
        )
        tags = list()
        tags = response['Item']['tags']
        return tags

    #Create a new role to tags mapping
    def set_role_tags(self, role_name, tags):
        role = self.iam_resource.Role(role_name)
        put_item_response = self.table.put_item(
            Item={
                "role_arn": role.arn,
                "tags": tags,
            },
            ReturnValues='NONE'
        )
        return put_item_response
