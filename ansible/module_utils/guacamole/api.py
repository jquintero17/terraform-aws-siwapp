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
from urllib.parse import quote
from requests.packages.urllib3 import disable_warnings
from requests import Session
from requests.models import PreparedRequest
req = PreparedRequest()

# Disable SSL Warnings
disable_warnings()

GUACAMOLE_USERS = 'users'
GUACAMOLE_CONNECTION_GROUPS = 'connectionGroups'
GUACAMOLE_CONNECTIONS = 'connections'
GUACAMOLE_PERMISSIONS = 'permissions'
GUACAMOLE_USER_GROUPS = 'userGroups'

GUACAMOLE_PROVIDER_SPEC = {
    'host': dict(type='str',
                      required=False,
                      fallback=(env_fallback, ['GUACAMOLE_HOST']),
                 ),
    'username': dict(type='str',
                     aliases=['user', 'admin'],
                     required=False,
                     fallback=(env_fallback, ['GUACAMOLE_USERNAME'])),
    'password': dict(type='str',
                     aliases=['pass', 'pwd'],
                     required=False,
                     no_log=True,
                     fallback=(env_fallback, ['GUACAMOLE_PASSWORD'])),
    'verify': dict(type='bool', default=False),
    'silent_ssl_warnings': dict(type='bool', default=True),
    'timeout': dict(type='int', default=10),
    'max_retries': dict(type='int', default=3),
}


class GuacamoleApiBase(object):
    ''' Base class for implementing Guacamole API '''
    provider_spec = {'provider': dict(
        type='dict', options=GUACAMOLE_PROVIDER_SPEC)}

    def __init__(self, provider):
        if not set(provider.keys()).issubset(GUACAMOLE_PROVIDER_SPEC.keys()):
            raise ValueError(
                'invalid or unsupported keyword argument for connector')
        for key, value in iteritems(GUACAMOLE_PROVIDER_SPEC):
            if key not in provider:
                # apply default values from NIOS_PROVIDER_SPEC since we cannot just
                # assume the provider values are coming from AnsibleModule
                if 'default' in value:
                    provider[key] = value['default']
                # override any values with env variables unless they were
                # explicitly set
                env = ('GUACAMOLE_%s' % key).upper()
                if env in os.environ:
                    provider[key] = os.environ.get(env)
                # if key is required but still not defined raise Exception
                if key not in provider and 'required' in value and value['required']:
                    raise ValueError('option: %s is required' % key)
        self.session = Session()
        # self.module.fail_json(msg=json.dumps(os.environ))
        self.session.verify = provider['verify']
        self.session.silent_ssl_warnings = provider['silent_ssl_warnings']
        self.session.timeout = provider['timeout']
        self.session.max_retries = provider['max_retries']
        self.login(provider)
        self.host = provider['host']
        self.session.headers.update({
            'Content-Type': "application/json",
        })

        self.uri = 'https://%s/api/session/data/mysql/' % provider['host']

    def login(self, provider):
        login_url = 'https://%s/api/tokens' % provider['host']
        params = dict(
            username=provider['username'],
            password=provider['password']
        )
        headers = {
            'Content-Type': "application/x-www-form-urlencoded"
        }
        req.prepare_url(login_url, params)
        resp = self.session.post(req.url, headers=headers)
        if resp.status_code != 200:
            self.module.fail_json(
                msg="Unable to login to guacamole with provided credentials")
        else:
            self.token = resp.json()['authToken']

    def logout(self):
        logout_url = 'https://%s/api/tokens/%s' % (
            self.host, self.token)
        self.session.delete(logout_url)

    def req(self, path):
        req.prepare_url('%s%s' % (self.uri, path), dict(token=self.token))
        return req.url

    def handle_exception(self, method_name, exc, task):
        ''' Handles any exceptions raised
        This method is called when an unexpected response
        code is returned from a Guacamole API call
        '''
        self.module.fail_json(
            msg=exc.text,
            code=exc.status_code,
            operation=method_name,
            task=task
        )


class GuacamoleApiModule(GuacamoleApiBase):
    ''' Implements Guacamole API for executing a guacamole module '''

    def __init__(self, module):
        self.module = module
        provider = module.params.get(
            'provider') if module.params.get('provider') else dict()
        try:
            super(GuacamoleApiModule, self).__init__(provider)
        except Exception as exc:
            self.module.fail_json(msg=to_text(exc))

    def create_user(self, user):
        path = GUACAMOLE_USERS
        req_payload = {
            "username": user,
            "attributes": {
                "expired": "",
                "access-window-start": "",
                "access-window-end": "",
                "disabled": "",
                "valid-until": "",
                "valid-from": ""
            }
        }
        prepared_url = self.req(path)
        resp = self.session.post(prepared_url, data=json.dumps(req_payload))
        if resp.status_code != 200:
            self.handle_exception('post', resp, 'add_user')
        return resp.json()

    def delete_user(self, user):
        path = '%s/%s' % (GUACAMOLE_USERS, user)
        prepared_url = self.req(path)
        resp = self.session.delete(prepared_url)
        if resp.status_code != 204:
            self.handle_exception('delete', resp, 'delete_user')
        return

    def get_users(self, target=None):
        path = GUACAMOLE_USERS
        prepared_url = self.req(path)
        resp = self.session.get(prepared_url)
        if resp.status_code != 200:
            self.handle_exception('get', resp, 'get_users')
        if target:
            for (k, v) in iteritems(resp.json()):
                if k == target:
                    return v
            return None
        return resp.json()

    def get_connection_group(self, target):
        path = '%s/%s' % (GUACAMOLE_CONNECTION_GROUPS, target)
        prepared_url = self.req(path)
        resp = self.session.get(prepared_url)
        if resp.status_code != 200:
            self.handle_exception('get', resp, 'get_connection_group')
        return resp.json()

    def get_connection(self, target):
        path = '%s/%s' % (GUACAMOLE_CONNECTIONS, target)
        prepared_url = self.req(path)
        resp = self.session.get(prepared_url)
        if resp.status_code != 200:
            self.handle_exception('get', resp, 'get_connection')
        return resp.json()

    def get_connections(self):
        path = '%s/ROOT/tree' % GUACAMOLE_CONNECTION_GROUPS
        prepared_url = self.req(path)
        resp = self.session.get(prepared_url)
        if resp.status_code != 200:
            self.handle_exception('get', resp, 'get_connection_group')
        connection_paths = {}
        def walk(connection, parent='ROOT'):
            for group in connection['childConnectionGroups']:
                connection_paths['%s/%s' % (parent, group['name'])] = group['identifier']
                if 'childConnections' in group:
                    for child_connection in group['childConnections']:
                        connection_paths['%s/%s/%s' % (parent, group['name'], child_connection['name'])] = child_connection['identifier']
                if 'childConnectionGroups' in group:
                        walk(group, parent='%s/%s' % (parent, group['name']))
        walk(resp.json())
        return connection_paths

    def create_connection_group(self, name, parent_id):
        path = GUACAMOLE_CONNECTION_GROUPS
        prepared_url = self.req(path)
        req_payload = {
            "parentIdentifier": parent_id,
            "name": name,
            "type": "ORGANIZATIONAL",
            "attributes": {
                "max-connections": "",
                "max-connections-per-user": "",
                "enable-session-affinity": ""
            }
        }
        resp = self.session.post(prepared_url, data=json.dumps(req_payload))
        if resp.status_code != 200:
            self.handle_exception('post', resp, 'create_connection_group')
        return resp.json()

    def delete_connection_group(self, group_id):
        path = '%s/%s' % (GUACAMOLE_CONNECTION_GROUPS, group_id)
        prepared_url = self.req(path)
        resp = self.session.delete(prepared_url)
        if resp.status_code != 204:
            self.handle_exception('delete', resp, 'delete_connection_group')
        return

    def create_connection(self, name, hostname, type, parent_id, user, key=None, password=None):
        path = GUACAMOLE_CONNECTIONS
        prepared_url = self.req(path)
        req_payload = {}
        if type == 'ssh':
            req_payload = {
                "parentIdentifier": parent_id,
                "name": name,
                "protocol": "ssh",
                "parameters": {
                    "port": "22",
                    "read-only": "",
                    "swap-red-blue": "",
                    "cursor": "",
                    "color-depth": "",
                    "clipboard-encoding": "",
                    "dest-port": "",
                    "recording-exclude-output": "",
                    "recording-exclude-mouse": "",
                    "recording-include-keys": "",
                    "create-recording-path": "",
                    "enable-sftp": "",
                    "sftp-port": "",
                    "sftp-server-alive-interval": "",
                    "enable-audio": "",
                    "font-size": "10",
                    "server-alive-interval": "",
                    "backspace": "",
                    "terminal-type": "",
                    "create-typescript-path": "",
                    "hostname": hostname,
                    "username": user,
                    "private-key": key,
                    "color-scheme": "green-black"
                },
                "attributes": {
                    "max-connections": "",
                    "max-connections-per-user": "",
                    "weight": "",
                    "failover-only": "",
                    "guacd-port": "",
                    "guacd-encryption": ""
                }
            }
        elif type == 'rdp':
            req_payload = {
                "parentIdentifier": parent_id,
                "name": name,
                "protocol": "rdp",
                "parameters": {
                    "port": "3389",
                    "read-only": "",
                    "swap-red-blue": "",
                    "cursor": "",
                    "color-depth": "",
                    "clipboard-encoding": "",
                    "dest-port": "",
                    "recording-exclude-output": "",
                    "recording-exclude-mouse": "",
                    "recording-include-keys": "",
                    "create-recording-path": "",
                    "enable-sftp": "",
                    "sftp-port": "",
                    "sftp-server-alive-interval": "",
                    "enable-audio": "",
                    "security": "nla",
                    "disable-auth": "",
                    "ignore-cert": "true",
                    "gateway-port": "",
                    "server-layout": "",
                    "console": "",
                    "width": "",
                    "height": "",
                    "dpi": "",
                    "resize-method": "display-update",
                    "console-audio": "",
                    "disable-audio": "",
                    "enable-audio-input": "",
                    "enable-printing": "",
                    "enable-drive": "",
                    "create-drive-path": "",
                    "enable-wallpaper": "true",
                    "enable-theming": "",
                    "enable-font-smoothing": "true",
                    "enable-full-window-drag": "",
                    "enable-desktop-composition": "",
                    "enable-menu-animations": "",
                    "disable-bitmap-caching": "",
                    "disable-offscreen-caching": "",
                    "disable-glyph-caching": "",
                    "preconnection-id": "",
                    "hostname": hostname,
                    "username": user,
                    "password": password
                },
                "attributes": {
                    "max-connections": "",
                    "max-connections-per-user": "",
                    "weight": "",
                    "failover-only": "",
                    "guacd-port": "",
                    "guacd-encryption": "",
                    "guacd-hostname": ""
                }
            }
        elif type == 'xrdp':
            req_payload = {
                "parentIdentifier": parent_id,
                "name": name,
                "protocol": "rdp",
                "parameters": {
                    "port": "3389",
                    "read-only": "",
                    "swap-red-blue": "",
                    "cursor": "",
                    "color-depth": "",
                    "clipboard-encoding": "",
                    "dest-port": "",
                    "recording-exclude-output": "",
                    "recording-exclude-mouse": "",
                    "recording-include-keys": "",
                    "create-recording-path": "",
                    "enable-sftp": "",
                    "sftp-port": "",
                    "sftp-server-alive-interval": "",
                    "enable-audio": "",
                    "security": "any",
                    "disable-auth": "",
                    "ignore-cert": "true",
                    "gateway-port": "",
                    "server-layout": "",
                    "console": "",
                    "width": "",
                    "height": "",
                    "dpi": "",
                    "resize-method": "",
                    "console-audio": "",
                    "disable-audio": "",
                    "enable-audio-input": "",
                    "enable-printing": "",
                    "enable-drive": "",
                    "create-drive-path": "",
                    "enable-wallpaper": "true",
                    "enable-theming": "",
                    "enable-font-smoothing": "true",
                    "enable-full-window-drag": "",
                    "enable-desktop-composition": "",
                    "enable-menu-animations": "",
                    "disable-bitmap-caching": "",
                    "disable-offscreen-caching": "",
                    "disable-glyph-caching": "",
                    "preconnection-id": "",
                    "hostname": hostname,
                    "username": user,
                    "password": password
                },
                "attributes": {
                    "max-connections": "",
                    "max-connections-per-user": "",
                    "weight": "",
                    "failover-only": "",
                    "guacd-port": "",
                    "guacd-encryption": "",
                    "guacd-hostname": ""
                }
            }
        resp = self.session.post(prepared_url, data=json.dumps(req_payload))
        if resp.status_code != 200:
            self.handle_exception('post', resp, 'create_connection')
        return resp.json()

    def delete_connection(self, id):
        path = '%s/%s' % (GUACAMOLE_CONNECTIONS, id)
        prepared_url = self.req(path)
        resp = self.session.delete(prepared_url)
        if resp.status_code != 204:
            self.handle_exception('delete', resp, 'delete_connection')
        return

    def add_connection_to_user(self, user, connection):
        path = '%s/%s/%s' % (GUACAMOLE_USERS, user, GUACAMOLE_PERMISSIONS)
        prepared_url = self.req(path)
        connection_type = 'Group' if connection['sub_type'] == 'group' else ''
        req_payload = [{
            "op": "add",
            "path": "/connection%sPermissions/%s" % (connection_type, connection['identifier']),
            "value": "READ"
        }]
        resp = self.session.patch(prepared_url, data=json.dumps(req_payload))
        if resp.status_code != 204:
            self.handle_exception('delete', resp, 'add_connection_to_user')
        return

    def remove_connection_from_user(self, user, connection):
        path = '%s/%s/%s' % (GUACAMOLE_USERS, user, GUACAMOLE_PERMISSIONS)
        prepared_url = self.req(path)
        connection_type = 'Group' if connection['sub_type'] == 'group' else ''
        req_payload.append = [{
            "op": "remove",
            "path": "/connection%sPermissions/%s" % (connection_type, connection['identifier']),
            "value": "READ"
        }]
        resp = self.session.patch(prepared_url, data=json.dumps(req_payload))
        if resp.status_code != 204:
            self.handle_exception('delete', resp, 'remove_connection_from_user')
        return

    def get_user_permissions(self, user, ids_only=False):
        path = '%s/%s/%s' % (GUACAMOLE_USERS, user, GUACAMOLE_PERMISSIONS)
        prepared_url = self.req(path)
        resp = self.session.get(prepared_url)
        if resp.status_code != 200:
            self.handle_exception('get', resp, 'get_user_permissions')
        if ids_only:
            ids = {
                'connection': {},
                'group': {}
            }
            for id in iterkeys(resp.json()['connectionPermissions']):
                ids['connection'][id] = 'connection'
            for id in iterkeys(resp.json()['connectionGroupPermissions']):
                ids['group'][id] = 'group'
            return ids
        return resp.json()

    def get_user_group(self, target):
        path = f"{GUACAMOLE_USER_GROUPS}/{quote(target)}"
        prepared_url = self.req(path)
        resp = self.session.get(prepared_url)
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            self.handle_exception('get', resp, 'get_user_group')
        return resp.json()
    
    def create_user_group(self, name):
        path = GUACAMOLE_USER_GROUPS
        prepared_url = self.req(path)
        req_payload = {
            "identifier": name,
            "attributes": {
                "disabled": ""
            }
        }
        resp = self.session.post(prepared_url, data=json.dumps(req_payload))
        if resp.status_code != 200:
            self.handle_exception('post', resp, 'create_user_group')
        return resp.json()

    def delete_user_group(self, name):
        path = f"{GUACAMOLE_USER_GROUPS}/{quote(name)}"
        prepared_url = self.req(path)
        resp = self.session.delete(prepared_url)
        if resp.status_code != 204:
            self.handle_exception('delete', resp, 'delete_user_group')
        return    