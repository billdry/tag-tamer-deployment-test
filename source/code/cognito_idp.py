#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# Author - Bill Dry

# Purpose - functions to retrieve information regarding Amazon Cognito 
# user pools & users

# Import AWS module for python
import botocore
import boto3
# Import logging module
import logging

log = logging.getLogger(__name__)

# Function to return the authenticated user's user pool group ARN's
def get_user_group_arns(user_name, user_pool_id, region):
    try:
        cognito_idp_groups = dict()
        cognito_idp_client = boto3.client('cognito-idp', region_name=region)
        cognito_idp_groups = cognito_idp_client.admin_list_groups_for_user(
            Username=user_name,
            UserPoolId=user_pool_id
        )
        # initially support one Cognito user pool group per user
        group_role_arn = cognito_idp_groups['Groups'][0]['RoleArn']
    except botocore.exceptions.ClientError as error:
        log.error("Boto3 API returned error: {}".format(error))
        group_role_arn = False
    return group_role_arn