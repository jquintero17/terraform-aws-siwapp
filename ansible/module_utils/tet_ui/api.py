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
from ansible.module_utils._text import to_native
import json
from requests import Session, Request
from bs4 import BeautifulSoup
from requests.packages.urllib3 import disable_warnings

# Disable SSL Warnings
disable_warnings()

class UISession(object):
    def __init__(self):
        self.site = None
        self.username = None
        self.user_id = None
        self.password = None
        self.csrf = None
        self.session = None
        self.logged_in = False
        self.base_headers = None
        self.root_app_scope = None
        self.app_scope = None
    
    def login(self,user,password,site):
        self.ServerConnect = False
        self.site = site
        self.username = user
        self.password = password
        try:
            self.session = Session()
            url = 'https://{}/h4_users/sign_in'.format(site)
            response = self.session.get(url, verify=False)
            html_soup = BeautifulSoup(response.text, 'html.parser')
            token = html_soup.find('input', attrs = {'name':'authenticity_token'})['value']
            self.csrf = token

            url = 'https://{}/h4_users/sign_in'.format(site)
            payload = {'authenticity_token': token,
            'h4_user[email]': self.username,
            'h4_user[password]': password,
            'h4_user[otp_attempt]': None,
            'h4_user[remember_me]': 0,
            'commit': 'Sign in',
            'utf8': '&#x2713;'}

            self.base_headers = {
                'Host': site,
                'Connection': 'keep-alive',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'X-CSRF-Token':token
                }

            headers = dict(self.base_headers)
            # del headers['X-CSRF-Token']
            headers['Content-Type']='application/x-www-form-urlencoded'
            headers['Referrer']='https://{}/h4_users/sign_in'.format(site)
            headers['Accept']='application/json, text/plain, */*'

            req = Request('POST',  url, data=payload, headers=headers)
            prepped = self.session.prepare_request(req)
            resp = self.session.send(prepped,verify=False)
            if resp.status_code == 200 or resp.status_code == 302:
                self.logged_in = True
                path = '/current_user.json?concise=true'
                r = self.request(path=path,method='GET')
                self.root_app_scope = r.json()['preferences']['root_app_scope']
                self.app_scope = r.json()['preferences']['app_scope']
                self.user_id = r.json()['id']
                self.get_csrf()
                self.base_headers['Origin']='https://{}'.format(site)
                self.base_headers['Referer']='https://{}'.format(site)
                self.base_headers['cache-control']='no-cache'
                return True
            else:
                self.logged_in = False
                return False

        except:
            self.logged_in = False
            self.session = None
            return False
    
    def get_csrf(self):
        r = self.request(path='/',method='GET')
        html_soup = BeautifulSoup(r.text, 'html.parser')
        token = html_soup.find('meta', attrs = {'name':'csrf-token'})['content']
        self.csrf = token
        self.base_headers['X-CSRF-Token'] = token

    def logout(self):
        url = "https://{}/lab/nbs/hub/h4_nb_logout".format(self.site)
        self.base_headers['Accept']='application/json, text/plain, */*'
        r = self.session.post(url,headers=self.base_headers)
        url = "https://{}/logout".format(self.site)
        r = self.session.post(url,headers=self.base_headers)
        self.site = None
        self.user = None
        self.password = None
        self.csrf = None
        self.session = None
        self.logged_in = False
        self.headers = None
    
    def set_scope(self,scope_id):
        data = {'value':scope_id}
        r = self.request(path='/api/preferences/app_scope_id.json',method='PUT',json=data)
        if r.status_code == 200:
            self.root_app_scope = r.json()['preferences']['root_app_scope']
            self.app_scope = r.json()['preferences']['app_scope']
        elif r.status_code == 422:
            self.get_csrf()
            r = self.request(path='/api/preferences/app_scope_id.json',method='PUT',json=data)
            self.root_app_scope = r.json()['preferences']['root_app_scope']
            self.app_scope = r.json()['preferences']['app_scope']
        return r

    def request(self, path, method, params=None, data=None, files=None,add_headers=None,json=None,verify=False):
        if self.logged_in == False:
            return {'success':0,'error':'You must be log in first.'}
        if add_headers != None:
            headers = self.base_headers.copy()
            headers.update(add_headers)
        else:
            headers = self.base_headers
        if method.lower() == 'get':
            r = self.session.get('https://{}{}'.format(self.site,path), headers=headers, params=params, data=data, allow_redirects=True)
            return r
        ### NEEDS TESTING
        elif method.lower() == 'post':
            r = self.session.post('https://{}{}'.format(self.site,path), headers=headers, params=params, data=data, files=files,json=json, allow_redirects=True)
            return r
        ### NEEDS TESTING
        elif method.lower() == 'delete':
            r = self.session.delete('https://{}{}'.format(self.site,path), headers=headers, params=params, data=data)
            return r
        elif method.lower() == 'put':
            headers = dict(self.base_headers)
            headers['Content-Type']='application/json;charset=UTF-8'
            headers['Accept']='application/json, text/plain, */*'
            r = self.session.put('https://{}{}'.format(self.site,path), headers=headers, params=params, json=json)
            return r