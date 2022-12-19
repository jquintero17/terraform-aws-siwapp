#!/usr/bin/python
# coding: utf-8 -*-

# (c) 2017, Wayne Witzel III <wayne@riotousliving.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: tower_inventory
version_added: "2.3"
author: "Wayne Witzel III (@wwitzel3)"
short_description: create, update, or destroy Ansible Tower inventory.
description:
    - Create, update, or destroy Ansible Tower inventories. See
      U(https://www.ansible.com/tower) for an overview.
options:
    name:
      description:
        - The name to use for the inventory.
      required: True
    description:
      description:
        - The description to use for the inventory.
    organization:
      description:
        - Organization the inventory belongs to.
      required: True
    variables:
      description:
        - Inventory variables. Use C(@) to get from file.
    kind:
      description:
        - The kind field. Cannot be modified after created.
      default: ""
      choices: ["", "smart"]
      version_added: "2.7"
    host_filter:
      description:
        -  The host_filter field. Only useful when C(kind=smart).
      version_added: "2.7"
    state:
      description:
        - Desired state of the resource.
      default: "present"
      choices: ["present", "absent"]
extends_documentation_fragment: tower
'''


EXAMPLES = '''
- name: Add tower inventory
  tower_inventory:
    name: "Foo Inventory"
    description: "Our Foo Cloud Servers"
    organization: "Bar Org"
    state: present
    tower_config_file: "~/tower_cli.cfg"
'''

from ansible.module_utils.guacamole.api import GuacamoleApiModule
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import iteritems, iterkeys

def main():

    argument_spec = dict(
        provider=dict(required=True),
        name=dict(type='str', required=True),
        state=dict(required=True, choices=['present', 'absent'])
    )
    argument_spec.update(GuacamoleApiModule.provider_spec)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    guac_module = GuacamoleApiModule(module)

    # These are all elements we put in our return JSON object for clarity
    result = dict(
        failed=False,
        object=None,
    )

    name = 'ROOT/%s' % module.params.get('name')
    state = module.params.get('state')

    changed = False

    connection_map = guac_module.get_connections()
    existing_group = None
    if name in iterkeys(connection_map):
        existing_group = guac_module.get_connection_group(connection_map[name])
    parent_id = None

    # Get parent if not existent
    if len(name.split('/')) > 2 and not existing_group:
        target = '/'.join(name.split('/')[:-1])
        parent_id = connection_map[target] if target in iterkeys(connection_map) else None
    else:
        parent_id = 'ROOT'

    if not parent_id:
        module.fail_json(msg='Unable to find parent group: %s' %
                         '/'.join(name.split('/')[:-1]))

    # ---------------------------------
    # STATE == 'present'
    # ---------------------------------
    if state == 'present':
        if not existing_group:
            changed = True
            if not module.check_mode:
                result['object'] = guac_module.create_connection_group(
                    name=name.split('/')[-1], parent_id=parent_id)
        else:
            result['object'] = existing_group
        result['object']['sub_type'] = 'group'

    # ---------------------------------
    # STATE == 'absent'
    # ---------------------------------
    if state == 'absent':
        if existing_group:
            changed = True
            if not module.check_mode:
                guac_module.delete_connection_group(
                    existing_group['identifier'])
            else:
                result['object'] = existing_group

    guac_module.logout()
    module.exit_json(changed=changed, **result)


if __name__ == '__main__':
    main()
