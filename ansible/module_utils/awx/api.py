# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# (c) 2018 Red Hat Inc.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import os
from functools import partial
from ansible.module_utils._text import to_native
from ansible.module_utils.six import iteritems, iterkeys
from ansible.module_utils._text import to_text
from ansible.module_utils.basic import env_fallback

import json
from urllib2 import quote
from requests.packages.urllib3 import disable_warnings
from requests import Session
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta
from time import sleep


# Disable SSL Warnings
disable_warnings()

AWX_PROVIDER_SPEC = {
    'endpoint': dict(type='str',required=True, aliases=['host','server']),
    'token': dict(type='str',required=True),
    'verify': dict(type='bool', default=False),
    'silent_ssl_warnings': dict(type='bool', default=True),
    'timeout': dict(type='int', default=10),
    'max_retries': dict(type='int', default=3),
}

class AwxApiBase(object):
    ''' Base class for implementing AWX API '''
    provider_spec = {'provider': dict(type='dict', options=AWX_PROVIDER_SPEC)}

    def __init__(self, provider):
        if not set(provider.keys()).issubset(AWX_PROVIDER_SPEC.keys()):
            raise ValueError('invalid or unsupported keyword argument for connector')
        for key, value in iteritems(AWX_PROVIDER_SPEC):
            if key not in provider:
                # apply default values from NIOS_PROVIDER_SPEC since we cannot just
                # assume the provider values are coming from AnsibleModule
                if 'default' in value:
                    provider[key] = value['default']
                # override any values with env variables unless they were
                # explicitly set
                env = ('AWX_%s' % key).upper()
                if env in os.environ:
                    provider[key] = os.environ.get(env)
                # if key is required but still not defined raise Exception
                if key not in provider and 'required' in value and value['required']:
                    raise ValueError('option: %s is required' % key)
        self.session = Session()
        self.session.headers.update({
            'Authorization': 'Bearer %s' % provider['token']
        })
        self.session.verify = provider['verify']
        self.session.silent_ssl_warnings = provider['silent_ssl_warnings']
        self.session.timeout = provider['timeout']
        self.session.max_retries = provider['max_retries']
        self.uri = 'https://%s/api/v2/' % provider['endpoint']

    def handle_exception(self, method_name, exc):
        ''' Handles any exceptions raised
        This method is called when an unexpected response
        code is returned from a AWX API call
        '''
        self.module.fail_json(
            msg=exc.text,
            code=exc.status_code,
            operation=method_name
        )

    def test_connectivity(self):
        resp = self.session.get(self.uri + 'ping')
        if resp.status_code != 200:
            return False
        return True

    def get_owner_inventories(self, cec):
        resp = self.session.get(self.uri + 'inventories/?variables__contains=' + quote("'deployment_owner': '%s'" % cec))
        if resp.status_code == 200:
            return resp.json()
        self.handle_exception('get',resp)

    def get_deployment_inventories(self, property='name'):
        inventories = []
        page_size = 10
        resp = self.session.get(self.uri + 'inventories/?page_size={}&variables__contains={}'.format(page_size, quote("'deployment_owner'")))
        while True:
            if resp.status_code == 200:
                inventories += [ inventory[property] for inventory in resp.json()['results'] ]
                if resp.json()['next']:
                    resp = self.session.get(self.uri.split('/api')[0] + resp.json()['next'])
                else:
                    return inventories
            else:
                self.handle_exception('get',resp)

    def get_inventory_by_name(self, name):
        resp = self.session.get(self.uri + 'inventories/?name__iexact=' + quote(name))
        if resp.status_code == 200:
            return resp.json()['results'][0] if 'results' in resp.json() and len(resp.json()['results']) > 0 else None
        return None

    def get_credential(self, name):
        resp = self.session.get(self.uri + 'credentials/?name__iexact=' + quote(name))
        if resp.status_code == 200 and len(resp.json()['results']) > 0:
            return resp.json()['results'][0]
        self.handle_exception('get',resp)

    def delete_inventory(self, id):
        resp = self.session.delete(self.uri + 'inventories/{}/'.format(id))
        return True if resp.status_code == 200 else False

    def create_inventory(self, name, description, organization):
        req_payload = dict(
            name=name,
            description=description,
            organization=organization
        )
        resp = self.session.post(self.uri + 'inventories/')
        if resp.status_code == 200:
            return resp.json()
        self.handle_exception('post',resp)

    def get_inventory_groups(self, id):
        resp = self.session.get(self.uri + 'inventories/{}/groups/'.format(id))
        return resp.json()['results'] if 'results' in resp.json() and len(resp.json()['results']) > 0 else []

    def get_inventory_group_hosts(self, id):
        resp = self.session.get(self.uri + 'groups/{}/hosts'.format(id))
        return resp.json()['results'] if 'results' in resp.json() and len(resp.json()['results']) > 0 else []

    def get_inventory_group_vars(self, id):
        resp = self.session.get(self.uri + 'groups/{}/variable_data'.format(id))
        return resp.json()

    def get_template(self, name):
        resp = self.session.get(self.uri + 'job_templates/?name__iexact=' + quote(name))
        if resp.status_code == 200 and len(resp.json()['results']) > 0:
            return resp.json()['results'][0]
        self.handle_exception('get',resp)


class AwxApiModule(AwxApiBase):
    ''' Implements AWX API for executing a awx module '''
    def __init__(self, module):
        self.module = module
        provider = module.params.get('provider') if module.params.get('provider') else dict()
        try:
            super(AwxApiModule, self).__init__(provider)
        except Exception as exc:
            self.module.fail_json(msg=to_text(exc))
    
    def get_master_chatbot_list(self):
        all_deployments = dict(
            linux=[],
            microsoft=[]
        )
        inventories = self.get_deployment_inventories(property='id')
        for inventory in inventories:
            groups = self.get_inventory_groups(inventory)
            for group in groups:
                group_vars = self.get_inventory_group_vars(group['id'])
                hosts = self.get_inventory_group_hosts(group['id'])
                if hosts:
                    if group_vars and 'os_type' in group_vars:
                        all_deployments[group_vars['os_type']] += [ host['name'] for host in hosts ]
        return all_deployments

    def launch_job(self, name, inventory, credentials, extra_vars):
        template_id = self.get_template(name)['id']
        req_payload={}
        if extra_vars:
            req_payload['extra_vars'] = extra_vars
        if credentials:
            req_payload['credentials'] = []
            for credential in credentials:
                resolved_cred = self.get_credential(credential)
                req_payload['credentials'].append(resolved_cred['id'])
        if inventory:
            req_payload['inventory_id'] = self.get_inventory_by_name(inventory)['id']
        resp = self.session.post(self.uri + 'job_templates/{}/launch/'.format(template_id), json=req_payload)
        if resp.status_code == 201:
            return resp.json()
        self.handle_exception('post',resp)

    def wait_job(self, job_id, timeout, interval):
        end = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < end:
            resp = self.session.get(self.uri + 'jobs/{job_id}/'.format(job_id=job_id))
            status = resp.json()['status']
            if status.lower() == 'successful':
                return True
            elif status.lower() == 'failed':
                return False
            else:
                sleep(interval)
        return False
