#!/usr/bin/env python3

# copyright 2020 Bill Dry
# Tag Tamer Admin UI

# Import administrative functions
from admin import date_time_now
# Import Collections module to manipulate dictionaries
import collections
from collections import defaultdict, OrderedDict
# Import getter functions for Amazon Cognito
from cognito_idp import *
# Import getter/setter module for AWS Config
import config
from config import config
# Import getter/setter module for AWS resources & tags
import resources_tags
from resources_tags import resources_tags
# Import getter/setter module for AWS IAM
import iam
from iam import roles
# Import getter module for TagOption Groups
import get_tag_groups
from get_tag_groups import get_tag_groups
# Import setter module for TagOption Groups
import set_tag_groups
from set_tag_groups import set_tag_group
# Import getter/setter module for AWS Service Catalog
import service_catalog
from service_catalog import service_catalog
# Import getter/setter module for AWS SSM Parameter Store
import ssm_parameter_store
from ssm_parameter_store import ssm_parameter_store
# Import AWS STS functions
from sts import *
# Import Tag Tamer utility functions
from utilities import *

# Import flask framework module & classes to build API's
import flask, flask_wtf
from flask import Flask, jsonify, make_response, redirect, render_template, request, url_for
# Use only flask_awscognito version 1.2.6 or higher from Tag Tamer
from flask_awscognito import AWSCognitoAuthentication
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, set_access_cookies, unset_jwt_cookies
# Import JSON parser
import json
# Import logging module
import logging
# Import Regex
import re
#import OS module
import os
#import epoch time method
from time import time

# Read in Tag Tamer solution parameters
tag_tamer_parameters_file = open('tag_tamer_parameters.json', "rt")
tag_tamer_parameters = json.load(tag_tamer_parameters_file)

# logLevel options are DEBUG, INFO, WARNING, ERROR or CRITICAL
# Set logLevel in tag_tamer_parameters.json parameters file
if  re.search("DEBUG|INFO|WARNING|ERROR|CRITICAL", tag_tamer_parameters['parameters']['logging_level'].upper()):
    logLevel = tag_tamer_parameters['parameters']['logging_level'].upper()
else:
    logLevel = 'INFO'
logging.basicConfig(filename=tag_tamer_parameters['parameters']['log_file_location'],format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',datefmt='%m/%d/%Y %I:%M:%S %p')
# Set the base/root logging level for tag_tamer.py & all imported modules
logging.getLogger().setLevel(logLevel)
log = logging.getLogger('tag_tamer_main')
# Raise logging level for WSGI tool kit "werkzeug" that's German for "tool"
logging.getLogger('werkzeug').setLevel('ERROR')

# Get user-specified AWS regions
selected_regions = tag_tamer_parameters['parameters']['selected_regions']
region = selected_regions[0]
log.debug('The selected AWS region is: \"%s\"', region)

# Get AWS Service parameters from AWS SSM Parameter Store
ssm_ps = ssm_parameter_store(region)
# Fully qualified list of SSM Parameter names
ssm_parameter_full_names = ssm_ps.form_parameter_hierarchies(tag_tamer_parameters['parameters']['ssm_parameter_path'], tag_tamer_parameters['parameters']['ssm_parameter_names']) 
# SSM Parameters names & values
ssm_parameters = ssm_ps.ssm_get_parameter_details(ssm_parameter_full_names)

#print(ssm_parameters)

# Instantiate flask API applications
app = Flask(__name__)
app.secret_key = os.urandom(12)
app.config['AWS_DEFAULT_REGION'] = ssm_parameters['/tag-tamer/cognito-default-region-value']
app.config['AWS_COGNITO_DOMAIN'] = ssm_parameters['/tag-tamer/cognito-domain-value']
app.config['AWS_COGNITO_USER_POOL_ID'] = ssm_parameters['/tag-tamer/cognito-user-pool-id-value']
app.config['AWS_COGNITO_USER_POOL_CLIENT_ID'] = ssm_parameters['/tag-tamer/cognito-app-client-id']
app.config['AWS_COGNITO_USER_POOL_CLIENT_SECRET'] = ssm_parameters['/tag-tamer/cognito-app-client-secret-value']
app.config['AWS_COGNITO_REDIRECT_URL'] = ssm_parameters['/tag-tamer/cognito-redirect-url-value']
app.config['JWT_TOKEN_LOCATION'] = ssm_parameters['/tag-tamer/jwt-token-location']
app.config['JWT_ACCESS_COOKIE_NAME'] = ssm_parameters['/tag-tamer/jwt-access-cookie-name']
app.config['JWT_COOKIE_SECURE'] = ssm_parameters['/tag-tamer/jwt-cookie-secure']
app.config['JWT_COOKIE_CSRF_PROTECT'] = ssm_parameters['/tag-tamer/jwt-cookie-csrf-protect']

aws_auth = AWSCognitoAuthentication(app)
jwt = JWTManager(app)

# Allow users to sign into Tag Tamer via an Amazon Cognito User Pool
@app.route('/log-in')
@app.route('/sign-in')
def sign_in():
    return redirect(aws_auth.get_sign_in_url())

# Redirect the user to the Tag Tamer home page after successful AWS Cognito login
@app.route('/aws_cognito_redirect', methods=['GET'])
def aws_cognito_redirect():
    access_token = None
    access_token = aws_auth.get_access_token(request.args)
    if access_token:    
        response = make_response(render_template('redirect.html'))
        response.set_cookie('access_token', value=access_token)
        return response, 200
    else:
        return redirect(url_for('sign_in'))

# Get response delivers Tag Tamer home page
@app.route('/index.html', methods=['GET'])
@app.route('/index.htm', methods=['GET'])
@app.route('/index', methods=['GET'])
@app.route('/', methods=['GET'])
@aws_auth.authentication_required
def index():
    claims = aws_auth.claims
    # Get the user's assigned Cognito user pool group
    cognito_user_group_arn = get_user_group_arns(claims.get('username'), 
        ssm_parameters['/tag-tamer/cognito-user-pool-id-value'],
        ssm_parameters['/tag-tamer/cognito-default-region-value'])
    # Grant access if session time not expired & user assigned to Cognito user pool group
    if time() < claims.get('exp') and cognito_user_group_arn:
        log.info("User \"{}\" signed in on {}".format(claims.get('username'), date_time_now()))
        return render_template('index.html', user_name=claims.get('username'))
    else:
        return redirect('/sign-in')

def get_user_session_credentials():
    claims = aws_auth.claims
    # Get the user's assigned Cognito user pool group
    cognito_user_group_arn = get_user_group_arns(claims.get('username'), 
        ssm_parameters['/tag-tamer/cognito-user-pool-id-value'],
        ssm_parameters['/tag-tamer/cognito-default-region-value'])
    user_session_credentials = get_session_credentials(cognito_user_group_arn,
        claims.get('username'),
        ssm_parameters['/tag-tamer/cognito-default-region-value'])
    return user_session_credentials



# Get response delivers Tag Tamer actions page showing user choices as clickable buttons
@app.route('/actions', methods=['GET'])
@aws_auth.authentication_required
def actions():
    return render_template('actions.html')    

# Get response delivers HTML UI to select AWS resource types that Tag Tamer will find
# Post action initiates tag finding for user selected AWS resource types
@app.route('/find-tags', methods=['GET'])
@aws_auth.authentication_required
def find_tags():
    return render_template('find-tags.html')    

# Pass Get response to found-tags HTML UI
@app.route('/found-tags', methods=['POST'])
@aws_auth.authentication_required
def found_tags():
    resource_type, unit = get_resource_type_unit(request.form.get('resource_type'))
    session_credentials = get_user_session_credentials()
    inventory = resources_tags(resource_type, unit, region)
    sorted_tagged_inventory = inventory.get_resources_tags(**session_credentials)
    return render_template('found-tags.html', inventory=sorted_tagged_inventory)

# Delivers HTML UI to select AWS resource types to manage Tag Groups for
@app.route('/type-to-tag-group', methods=['GET'])
@aws_auth.authentication_required
def type_to_tag_group():
    return render_template('type-to-tag-group.html') 

# Post response to get tag groups attributes UI
@app.route('/get-tag-group-names', methods=['POST'])
@aws_auth.authentication_required
def get_tag_group_names():
    all_tag_groups = get_tag_groups(region)
    tag_group_names = all_tag_groups.get_tag_group_names()
    
    resource_type, _ = get_resource_type_unit(request.form.get('resource_type'))

    return render_template('display-tag-groups.html', inventory=tag_group_names, resource_type=resource_type)

# Post method to display edit UI for chosen tag group
@app.route('/edit-tag-group', methods=['POST'])
@aws_auth.authentication_required
def edit_tag_group():
    resource_type, unit = get_resource_type_unit(request.form.get('resource_type'))
    inventory = resources_tags(resource_type, unit, region)
    sorted_tag_values_inventory = inventory.get_tag_values()

    # If user does not select an existing Tag Group or enter 
    # a new Tag Group name reload this route until valid user input given
    if request.form.get('tag_group_name'):    
        selected_tag_group_name = request.form.get('tag_group_name')
        tag_group = get_tag_groups(region)
        tag_group_key_values = tag_group.get_tag_group_key_values(selected_tag_group_name)
        return render_template('edit-tag-group.html', resource_type=resource_type, selected_tag_group_name=selected_tag_group_name, selected_tag_group_attributes=tag_group_key_values, selected_resource_type_tag_values_inventory=sorted_tag_values_inventory)
    elif request.form.get('new_tag_group_name'):
        selected_tag_group_name = request.form.get('new_tag_group_name')
        tag_group_key_values = {}
        return render_template('edit-tag-group.html', resource_type=resource_type, selected_tag_group_name=selected_tag_group_name, selected_tag_group_attributes=tag_group_key_values, selected_resource_type_tag_values_inventory=sorted_tag_values_inventory)
    else:
        return render_template('type-to-tag-group.html')

# Post method to add or update a tag group
@app.route('/add-update-tag-group', methods=['POST'])
@aws_auth.authentication_required
def add_update_tag_group():
    #new_tag_group_name = request.form.get('new_tag_group_name')
    if request.form.get('new_tag_group_name') and request.form.get('new_tag_group_key_name'):
        tag_group_name = request.form.get('new_tag_group_name')
        tag_group_key_name = request.form.get('new_tag_group_key_name')
        tag_group_action = "create"
    elif request.form.get('selected_tag_group_name') and request.form.get('selected_tag_group_key_name'):
        tag_group_name = request.form.get('selected_tag_group_name')
        tag_group_key_name = request.form.get('selected_tag_group_key_name')
        tag_group_action = "update"
    else:
        return render_template('type-to-tag-group.html')

    tag_group_value_options = []
    form_contents = request.form.to_dict()
    for key, value in form_contents.items():
        if value == "checked":
            tag_group_value_options.append(key)
    if request.form.get("new_tag_group_values"):
        new_tag_group_values = request.form.get("new_tag_group_values").split(",")
        new_tag_group_values = [value.strip(" ") for value in new_tag_group_values]
        tag_group_value_options.extend(new_tag_group_values)

    tag_group = set_tag_group(region)
    if tag_group_action == "create":
        new_tag_group = tag_group.create_tag_group(tag_group_name, tag_group_key_name, tag_group_value_options)
    else:
        updated_tag_group = tag_group.update_tag_group(tag_group_name, tag_group_key_name, tag_group_value_options)

    tag_groups = get_tag_groups(region)
    tag_group_key_values = tag_groups.get_tag_group_key_values(tag_group_name)

    resource_type, unit = get_resource_type_unit(request.form.get('resource_type'))
    inventory = resources_tags(resource_type, unit, region)
    sorted_tag_values_inventory = inventory.get_tag_values()

    return render_template('edit-tag-group.html', resource_type=resource_type, selected_tag_group_name=tag_group_name, selected_tag_group_attributes=tag_group_key_values, selected_resource_type_tag_values_inventory=sorted_tag_values_inventory)

# Delivers HTML UI to select AWS resource type to tag using Tag Groups
@app.route('/select-resource-type', methods=['POST'])
@aws_auth.authentication_required
def select_resource_type():
    next_route  = request.form.get('next_route')
    if not next_route:
        next_route = 'tag_resources'
    return render_template('select-resource-type.html', destination_route=next_route) 

# Let user search existing tags then tag matching, existing resources 
@app.route('/tag-filter', methods=['POST'])
@aws_auth.authentication_required
def tag_filter():
    if request.form.get('resource_type'):
        return render_template('search-tag-resources-container.html', resource_type=request.form.get('resource_type')) 
    else:
        return render_template('select-resource-type.html', destination_route='tag_filter')

# Enter existing tag keys & values to search 
@app.route('/tag-based-search', methods=['GET'])
@aws_auth.authentication_required
def tag_based_search():
    if request.args.get('resource_type'):
        resource_type, unit = get_resource_type_unit(request.args.get('resource_type'))
        inventory = resources_tags(resource_type, unit, region)
        selected_tag_keys = inventory.get_tag_keys()
        selected_tag_values = inventory.get_tag_values()

        return render_template('tag-search.html', 
                resource_type=request.args.get('resource_type'),
                tag_keys=selected_tag_keys, 
                tag_values=selected_tag_values)
    else:
        return render_template('select-resource-type.html', destination_route='tag_filter')

# Delivers HTML UI to assign tags from Tag Groups to chosen AWS resources
@app.route('/tag_resources', methods=['GET','POST'])
@aws_auth.authentication_required
def tag_resources():
    #if request.form.get('tag_key1') or request.form.get('tag_key2'):
    if request.form.get('resource_type'):
        filter_elements = dict()
        if request.form.get('tag_key1'):
            filter_elements['tag_key1'] = request.form.get('tag_key1')
        if request.form.get('tag_value1'):
            filter_elements['tag_value1'] = request.form.get('tag_value1')
        if request.form.get('tag_key2'):
            filter_elements['tag_key2'] = request.form.get('tag_key2')
        if request.form.get('tag_value2'):
            filter_elements['tag_value2'] = request.form.get('tag_value2')
        if request.form.get('conjunction'):
            filter_elements['conjunction'] = request.form.get('conjunction')
        
        resource_type, unit = get_resource_type_unit(request.form.get('resource_type'))
        chosen_resource_inventory = resources_tags(resource_type, unit, region)
        chosen_resources = OrderedDict()
        chosen_resources = chosen_resource_inventory.get_resources(**filter_elements)
        tag_group_inventory = get_tag_groups(region)
        tag_groups_all_info = tag_group_inventory.get_all_tag_groups_key_values()
        return render_template('tag-resources.html', resource_type=resource_type, resource_inventory=chosen_resources, tag_groups_all_info=tag_groups_all_info) 
    else:
        return render_template('blank.html')

# Delivers HTML UI to assign tags from Tag Groups to chosen AWS resources
@app.route('/apply-tags-to-resources', methods=['POST'])
@aws_auth.authentication_required
def apply_tags_to_resources():
    if request.form.getlist('resources_to_tag'):
        resources_to_tag = []
        resources_to_tag = request.form.getlist('resources_to_tag')
        
        form_contents = request.form.to_dict()
        form_contents.pop("resources_to_tag")
    
        resource_type, unit = get_resource_type_unit(request.form.get('resource_type'))
        chosen_resources_to_tag = resources_tags(resource_type, unit, region) 
        form_contents.pop("resource_type")

        chosen_tags = []
        for key, value in form_contents.items():
            if value:
                tag_kv = {}
                tag_kv["Key"] = key
                tag_kv["Value"] = value
                chosen_tags.append(tag_kv)
        chosen_resources_to_tag.set_resources_tags(resources_to_tag, chosen_tags)
        
        updated_sorted_tagged_inventory = {}
        all_sorted_tagged_inventory = chosen_resources_to_tag.get_resources_tags()
        for resource_id in resources_to_tag:
            updated_sorted_tagged_inventory[resource_id] = all_sorted_tagged_inventory[resource_id]
        
        return render_template('updated-tags.html', inventory=updated_sorted_tagged_inventory)
    else:
        return render_template('blank.html')

# Retrieves AWS Service Catalog products & Tag Groups
@app.route('/get-service-catalog', methods=['GET'])
@aws_auth.authentication_required
def get_service_catalog():

    #Get the Tag Group names & associated tag keys
    tag_group_inventory = dict()
    tag_groups = get_tag_groups(region)
    tag_group_inventory = tag_groups.get_tag_group_names()

    #Get the Service Catalog product templates
    sc_product_ids_names = dict()
    #sc_product_names = list()
    sc_products = service_catalog(region)
    sc_product_ids_names = sc_products.get_sc_product_templates()
    

    return render_template('update-service-catalog.html', tag_group_inventory=tag_group_inventory, sc_product_ids_names=sc_product_ids_names)

# Updates AWS Service Catalog product templates with TagOptions using Tag Groups
@app.route('/set-service-catalog', methods=['POST'])
@aws_auth.authentication_required
def set_service_catalog():
    if request.form.getlist('tag_groups_to_assign') and request.form.getlist('chosen_sc_product_template_ids'):
        selected_tag_groups = list()
        selected_tag_groups = request.form.getlist('tag_groups_to_assign')
        sc_product_templates = list()
        sc_product_templates = request.form.getlist('chosen_sc_product_template_ids')

        #Get the Service Catalog product templates
        sc_product_ids_names = dict()
        sc_products = service_catalog(region)
        sc_product_ids_names = sc_products.get_sc_product_templates()

        #Assign every tag in selected Tag Groups to selected SC product templates
        updated_product_temp_tagoptions = defaultdict(list)
        sc_response = dict()
        for sc_prod_template_id in sc_product_templates:
            for tag_group_name in selected_tag_groups:
                sc_response.clear()
                sc_response = sc_products.assign_tg_sc_product_template(tag_group_name, sc_prod_template_id)
                updated_product_temp_tagoptions[sc_prod_template_id].append(sc_response)

        return render_template('updated-service-catalog.html', sc_product_ids_names=sc_product_ids_names, updated_product_temp_tagoptions=updated_product_temp_tagoptions)
    else:
        return redirect(url_for('get_service_catalog'))

# Retrieves AWS Config Rules & Tag Groups
@app.route('/find-config-rules', methods=['GET'])
@aws_auth.authentication_required
def find_config_rules():

    #Get the Tag Group names & associated tag keys
    tag_group_inventory = dict()
    tag_groups = get_tag_groups(region)
    tag_group_inventory = tag_groups.get_tag_group_names()

    #Get the AWS Config Rules
    config_rules_ids_names = dict()
    config_rules = config(region)
    config_rules_ids_names = config_rules.get_config_rules_ids_names()
    
    return render_template('find-config-rules.html', tag_group_inventory=tag_group_inventory, config_rules_ids_names=config_rules_ids_names)

# Updates AWS Config's required-tags rule using Tag Groups
@app.route('/update-config-rules', methods=['POST'])
@aws_auth.authentication_required
def set_config_rules():
    if request.form.getlist('tag_groups_to_assign') and request.form.getlist('chosen_config_rule_ids'):
        selected_tag_groups = list()
        selected_tag_groups = request.form.getlist('tag_groups_to_assign')
        selected_config_rules = list()
        selected_config_rules = request.form.getlist('chosen_config_rule_ids')
        config_rule_id = selected_config_rules[0]

        tag_groups = get_tag_groups(region)
        tag_group_key_values = dict()
        tag_groups_keys_values = dict()
        tag_count=1
        for group in selected_tag_groups:
            # A Required_Tags Config Rule instance accepts up to 6 Tag Groups
            if tag_count < 7:
                tag_group_key_values = tag_groups.get_tag_group_key_values(group)
                key_name = "tag{}Key".format(tag_count)
                value_name = "tag{}Value".format(tag_count)
                tag_groups_keys_values[key_name] = tag_group_key_values['tag_group_key']
                tag_group_values_string = ",".join(tag_group_key_values['tag_group_values'])
                tag_groups_keys_values[value_name] = tag_group_values_string
                tag_count+=1

        config_rules = config(region)
        config_rules.set_config_rules(tag_groups_keys_values, config_rule_id)
        updated_config_rule = config_rules.get_config_rule(config_rule_id)

        return render_template('updated-config-rules.html', updated_config_rule=updated_config_rule)
    else:
        return redirect(url_for('find_config_rules'))

# Retrieves AWS IAM Roles & Tag Groups
@app.route('/select-roles-tags', methods=['GET'])
@aws_auth.authentication_required
def select_roles_tags():
    tag_group_inventory = get_tag_groups(region)
    tag_groups_all_info = tag_group_inventory.get_all_tag_groups_key_values()

    iam_roles = roles(region)
    #Initially get AWS SSO Roles
    path_prefix = "/aws-reserved/sso.amazonaws.com/"
    roles_inventory = iam_roles.get_roles(path_prefix)

    return render_template('tag-roles.html', roles_inventory=roles_inventory, tag_groups_all_info=tag_groups_all_info)

# Assigns selected tags to roles for tagging newly created AWS resources
@app.route('/set-roles-tags', methods=['POST'])
@aws_auth.authentication_required
def set_roles_tags():
    if request.form.get('roles_to_tag'):
        role_name = request.form.get('roles_to_tag')
        form_contents = request.form.to_dict()
        form_contents.pop('roles_to_tag')

        chosen_tags = list()
        for key, value in form_contents.items():
            if value:
                tag_kv = {}
                tag_kv["Key"] = key
                tag_kv["Value"] = value
                chosen_tags.append(tag_kv)

        role_to_tag = roles(region)
        role_to_tag.set_role_tags(role_name, chosen_tags)

        return render_template('actions.html')
    else:
        return redirect(url_for('select_roles_tags'))

@app.route('/logout', methods=['GET'])
@aws_auth.authentication_required
def logout():
    claims = aws_auth.claims
    log.info("User \"{}\" signed out on {}".format(claims.get('username'), date_time_now()))
    response = make_response(render_template('logout.html'))
    unset_jwt_cookies(response)
    return response, 200       
