#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2018, Doron Chosnek
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: tetration_interface_intent
version_added: "2.7"
author: "Brandon Beck(@techBeck03)"
short_description: Configure Tetration interface config intents
description:
   - Configures interface config intents for Tetration VRFs
requirements:
    - tetpyclient
extends_documentation_fragment: tetration
options:
  vrf_name:
    description:
    - Name of VRF associated with interface intent
    required: no
  vrf_id:
    description:
    - UUID of VRF associated with interface intent
    required: no
  inventory_filter_name:
    description:
    - Name of inventory filter associated with interface intent
    required: no
  inventory_filter_id:
    description:
    - ID inventory filter associated with interface intent
    required: no
'''

EXAMPLES = r'''
- name: Get interface config intents
  tetration_interface_intent:
    vrf_name: vrf
    inventory_filter_name: filter
    state: query
    provider:
      host: "tetration-cluster@company.com"
      api_key: 1234567890QWERTY
      api_secret: 1234567890QWERTY
  connection: local
'''

from ansible.module_utils.basic import AnsibleModule
import csv
import os.path

from ansible.utils.display import Display
display = Display()

from time import sleep

def main():
    csv_spec=dict(
        csv_file=dict(type='str', required=True),
        csv_array=dict(type='list', required=False),
        row_dict=dict(type='dict', required=False),
        row_index=dict(type='int', required=False),
        field_names=dict(type='list', required=True)
    )

    module = AnsibleModule(
        argument_spec=csv_spec,
        supports_check_mode=True,
        required_one_of=[
            ['csv_array', 'row_dict']
        ],
        mutually_exclusive=[
            ['csv_array', 'row_dict']
        ]
    )

    # These are all elements we put in our return JSON object for clarity
    result = dict(
        changed=False,
        object=None,
    )

    csv_file = module.params['csv_file']
    csv_array = module.params['csv_array']
    row_dict = module.params['row_dict']
    row_index = module.params['row_index']
    fieldnames = module.params['field_names']
    row_string = ''

    # =========================================================================
    # Get current state of the object
    csv_contents = None
    with open(csv_file, 'r') as file:
        # read a list of lines into data
        csv_contents = file.readlines()
    for name in fieldnames:
        row_string += row_dict[name] + ','
    if row_index + 1 == len(csv_contents) - 1:
        row_string = row_string[:-1]
    else:
        row_string = row_string[:-1] + "\r\n"
    csv_contents[row_index + 1] = row_string
    result['object'] = csv_contents
    # # and write everything back
    with open(csv_file, 'w') as file:
        file.writelines( csv_contents )

    result['changed'] = True
    # Return result
    module.exit_json(**result)

if __name__ == '__main__':
    main()
