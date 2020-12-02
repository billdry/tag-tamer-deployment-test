#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# Getter & setter for AWS Config Rules

# Import administrative functions
from admin import execution_status
# Import AWS module for python
import botocore
import boto3
# Import JSON
import json
# Import logging module
import logging

log = logging.getLogger(__name__)

# Define AWS Config class to get/set items using Boto3
class config:
    
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
        self.config_client = this_session.client('config', region_name=self.region)

    #Get REQUIRED_TAGS Config Rule name & input parameters
    def get_config_rule(self, config_rule_id):
        response = dict()
        all_config_rules = dict()
        try:
            response = self.config_client.describe_config_rules()
            all_config_rules = response['ConfigRules']

            required_tags_config_rules = dict()
            input_parameters_dict = dict()
            for rule in all_config_rules:
                if rule['Source']['SourceIdentifier'] == 'REQUIRED_TAGS':
                    input_parameters_dict = json.loads(rule['InputParameters'])
                    required_tags_config_rules['ConfigRuleName'] = rule['ConfigRuleName']
                    required_tags_config_rules['ComplianceResourceTypes'] = rule['Scope']['ComplianceResourceTypes']
                    for key, value in input_parameters_dict.items():
                        required_tags_config_rules[key] = value
                    input_parameters_dict.clear()
            
            return required_tags_config_rules

        except botocore.exceptions.ClientError as error:
                errorString = "Boto3 API returned error: {}"
                log.error(errorString.format(error))

    #Get REQUIRED_TAGS Config Rule names & ID's
    def get_config_rules_ids_names(self):
        my_status = execution_status()
        response = dict()
        all_config_rules = dict()
        config_rules_ids_names = dict()
        try:
            response = self.config_client.describe_config_rules()
            all_config_rules = response['ConfigRules']
            for configRule in all_config_rules:
                if configRule['Source']['SourceIdentifier'] == 'REQUIRED_TAGS':
                    config_rules_ids_names[configRule['ConfigRuleId']] = configRule['ConfigRuleName']
            my_status.success(message='Resources Found!')    

        except botocore.exceptions.ClientError as error:
                errorString = "Boto3 API returned error: {}"
                log.error(errorString.format(error))
                if error.response['Error']['Code'] == 'AccessDeniedException' or error.response['Error']['Code'] == 'UnauthorizedOperation':
                    status_message = error.response['Error']['Code'] + ' - You are not authorized to view these resources'
                    my_status.error(message=status_message)
                else:
                    my_status.error(message=error.response['Error']['Message'])
                config_rules_ids_names['No Config rules found'] = 'No Config rules found'
        
        return config_rules_ids_names, my_status.get_status()

    #Set REQUIRED_TAGS Config Rule
    def set_config_rules(self, tag_groups_keys_values, config_rule_id):
        
        if len(tag_groups_keys_values):
            # convert selected Tag Groups into JSON for Boto3 input to
            # this Config Rule's underlying Lambda :
            input_parameters_json = json.dumps(tag_groups_keys_values)
            config_rule_current_parameters = dict()
            config_rule_current_parameters = self.get_config_rule(config_rule_id)
            try:
                self.config_client.put_config_rule(
                    ConfigRule={
                        'ConfigRuleId': config_rule_id,
                        'Scope': {
                            'ComplianceResourceTypes': config_rule_current_parameters['ComplianceResourceTypes']
                        },
                        'InputParameters': input_parameters_json,
                        'Source': {
                            'Owner': 'AWS',
                            'SourceIdentifier': 'REQUIRED_TAGS'
                        }    
                    }
                )
                log.debug('REQUIRED_TAGS Config Rule \"%s\" updated with these parameters: \"%s\"', config_rule_id, input_parameters_json)
            except botocore.exceptions.ClientError as error:
                errorString = "Boto3 API returned error: {}"
                log.error(errorString.format(error))

        else:
            return log.warning("Please select at least one Tag Group")