#!/usr/bin/env python
#
# Copyright 2012 Code Pasty
#
# A simple code sharing website.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import webapp2
from google.appengine.ext import db
from google.appengine.api import users

from Template_Handler import Handler
from Pasty import Pasty # The Pasty DB Class

#---- Webpage Handlers

class Home(Handler):    
    def get(self):
        paster = users.get_current_user()
        u = db.GqlQuery("SELECT * FROM Pasty ORDER BY Last_Modified DESC LIMIT 10")
        if u.count() < 1:
            u = None
        if paster:
            self.render('index.html', recent_pasties=u, logout_link=users.create_logout_url('/'), disable=not bool(paster))
        else:
            self.render('index.html', recent_pasties=u, login_link=users.create_login_url(self.request.uri), disable=not bool(paster))

    def post(self):
        paster = users.get_current_user()
        name    = self.request.get('name').strip()
        content = self.request.get('content').strip()

        if name and content and bool(paster):
            u = Pasty(Name = name, Content = content, User = paster)
            u.put()
            self.redirect('/pasty/%s' % u.key().id())
        else:
            self.redirect(users.create_login_url(self.request.uri))

  
class View_Pasty(Handler):
    def get(self, id):
        paster = users.get_current_user()
        u = Pasty.get_by_id(int(id))
        if u == None:
            self.error(404);
        else:
            is_owner = (u.User == paster)
            self.render("view_pasty.html", pasty=u, is_owner=is_owner, comments = {"1": {"Justin Ruggles": "Some issues here!", "Aneesh Dogra": "Some issues here!"}})
    
class Pasty_Manipulation(Handler):
    def delete_pasty(self, key):
        u = db.GqlQuery("SELECT * FROM Pasty WHERE __key__ = KEY('%s')" % (key))
        if u.count() == 1:
            db.delete(u)

    def get(self, action, key):
        actions = {'delete': self.delete_pasty}
        
        if action in actions:
                actions[action](key)
        
        self.redirect('/')

app = webapp2.WSGIApplication([(r'/'               , Home),
                               (r'/pasty/([0-9]+)',  View_Pasty),
                               (r'/pasty/(.+)/(.+)', Pasty_Manipulation)], debug=True)