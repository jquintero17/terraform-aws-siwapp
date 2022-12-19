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
from base64 import b64encode
from random import randint
from time import sleep


# Disable SSL Warnings
disable_warnings()

VMWARE_PROVIDER_SPEC = {
    'host': dict(type='str',
                      required=False,
                      fallback=(env_fallback, ['VMWARE_HOST']),
                      ),
    'user': dict(type='str',
                      aliases=['user', 'admin'],
                      required=False,
                      fallback=(env_fallback, ['VMWARE_USER'])),
    'password': dict(type='str',
                      aliases=['pass', 'pwd'],
                      required=False,
                      no_log=True,
                      fallback=(env_fallback, ['VMWARE_PASSWORD'])),
    'verify': dict(type='bool', default=False),
    'silent_ssl_warnings': dict(type='bool', default=True),
    'timeout': dict(type='int', default=10),
    'max_retries': dict(type='int', default=3),
}

class VmwareApiBase(object):
    ''' Base class for implementing Vmware API '''
    provider_spec = {'provider': dict(type='dict', options=VMWARE_PROVIDER_SPEC)}

    def __init__(self, provider):
        if not set(provider.keys()).issubset(VMWARE_PROVIDER_SPEC.keys()):
            raise ValueError('invalid or unsupported keyword argument for connector')
        for key, value in iteritems(VMWARE_PROVIDER_SPEC):
            if key not in provider:
                # apply default values from NIOS_PROVIDER_SPEC since we cannot just
                # assume the provider values are coming from AnsibleModule
                if 'default' in value:
                    provider[key] = value['default']
                # override any values with env variables unless they were
                # explicitly set
                env = ('VMWARE_%s' % key).upper()
                if env in os.environ:
                    provider[key] = os.environ.get(env)
                # if key is required but still not defined raise Exception
                if key not in provider and 'required' in value and value['required']:
                    raise ValueError('option: %s is required' % key)
        self.session = Session()
        # self.module.fail_json(msg=json.dumps(os.environ))
        auth_string = b64encode(b'%s:%s' % (provider['user'], provider['password']))
        self.session.headers.update({
            'Authorization': 'Basic %s' % auth_string,
            'Content-Type': "application/json",
        })
        self.session.verify = provider['verify']
        self.session.silent_ssl_warnings = provider['silent_ssl_warnings']
        self.session.timeout = provider['timeout']
        self.session.max_retries = provider['max_retries']
        self.uri = 'https://%s/rest/' % provider['host']
        self.session.post(self.uri + 'com/vmware/cis/session')
        del self.session.headers['Authorization']

    def handle_exception(self, method_name, exc, task):
        ''' Handles any exceptions raised
        This method is called when an unexpected response
        code is returned from a Vmware API call
        '''
        self.module.fail_json(
            msg=exc.text,
            code=exc.status_code,
            operation=method_name,
            task=task
        )



class VmwareApiModule(VmwareApiBase):
    ''' Implements Vmware API for executing a vmware module '''
    def __init__(self, module):
        self.module = module
        provider = module.params.get('provider') if module.params.get('provider') else dict()
        try:
            super(VmwareApiModule, self).__init__(provider)
            sleep(randint(2,10))
        except Exception as exc:
            self.module.fail_json(msg=to_text(exc))

    def get_categories(self):
        categories = []
        category_ids = self.session.get(self.uri + 'com/vmware/cis/tagging/category')
        if category_ids.status_code != 200:
            self.handle_exception('get',resp)
        if 'value' not in category_ids.json():
            return categories
        for id in category_ids.json()['value']:
            category = self.session.get(self.uri + 'com/vmware/cis/tagging/category/id:' + id)
            categories.append(category.json()['value'])
        return categories

    def get_tags(self):
        tags = []
        tag_ids = self.session.get(self.uri + 'com/vmware/cis/tagging/tag')
        if tag_ids.status_code != 200:
            self.handle_exception('get', tag_ids, 'get_tags')
        if 'value' not in tag_ids.json():
            return tags
        for id in tag_ids.json()['value']:
            tag = self.session.get(self.uri + 'com/vmware/cis/tagging/tag/id:' + id)
            tags.append(tag.json()['value'])
        return tags

    def create_tag(self, category, description, name):
        req_payload = dict(
            create_spec = dict(
                category_id = category['id'],
                description = "created by ansible",
                name = name
            )
        )
        resp = self.session.post(self.uri + 'com/vmware/cis/tagging/tag', data=json.dumps(req_payload))
        if resp.status_code == 400 and 'type' in resp.json() and 'already_exists' in resp.json()['type']:
            return None
        elif resp.status_code != 200:
            self.handle_exception('post', resp, 'create_tag')
        return dict(
            category_id = category['id'],
            description = description,
            name = name,
            id = resp.json()['value']
        )
    
    def attach_tags(self, object, tags):
        req_payload = dict(
            object_id = dict(
                id = object['vm'],
                type = 'VirtualMachine'
            ),
            tag_ids = tags
        )
        resp = self.session.post(self.uri + 'com/vmware/cis/tagging/tag-association?~action=attach-multiple-tags-to-object', data=json.dumps(req_payload))
        if resp.status_code != 200:
            self.handle_exception('post', resp, 'attach_tags')

    def detach_tags(self, object, tags):
        tag_ids = [ tag['id'] for tag in tags ]
        req_payload = dict(
            object_id = dict(
                id = object['vm'],
                type = 'VirtualMachine'
            ),
            tag_ids = tag_ids
        )
        resp = self.session.post(self.uri + 'com/vmware/cis/tagging/tag-association?~action=detach-multiple-tags-from-object', data=json.dumps(req_payload))
        if resp.status_code != 200:
            self.handle_exception('post', resp, 'detach_tags')
    
    def delete_tag(self, tag):
        resp = self.session.delete(self.uri + 'com/vmware/cis/tagging/tag/id:%s' % tag['id'])
        if resp.status_code != 200:
            self.handle_exception('delete', resp, 'delete_tag')

    def get_vm_by_name(self, name):
        resp = self.session.get(self.uri + 'vcenter/vm?filter.names.1=%s' % name)
        if resp.status_code != 200:
            self.handle_exception('get', resp, 'get_vm_by_name')
        elif 'value' not in resp.json():
            self.module.fail_json(msg='Unable to find vm named: %s' % name)
        elif len(resp.json()['value']) > 1:
            self.module.fail_json(msg='Multiple matches found for vm name: %s' % name)
        else:
            return resp.json()['value'][0]

    def get_attached_tags(self, vm):
        req_payload = dict(
            object_id = dict(
                id = vm['vm'],
                type = 'VirtualMachine'
            )
        )
        resp = self.session.post(self.uri + 'com/vmware/cis/tagging/tag-association?~action=list-attached-tags', data=json.dumps(req_payload))
        if resp.status_code != 200:
            self.handle_exception('get', resp, 'get_attached_tags')
        return resp.json()['value'] if 'value' in resp.json() else []
