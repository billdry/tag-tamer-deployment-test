#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# Tag Tamer administrative functions

from time import time, gmtime, strftime

# Return the date & current time
def date_time_now():
    now = gmtime()
    time_string = strftime("%d-%B-%Y at %H:%M:%S UTC", now)
    return time_string
  

