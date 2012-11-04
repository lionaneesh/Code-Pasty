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
import logging
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import memcache

from Template_Handler import Handler

#-- Database Classes

from Pasty   import Pasty
from Comment import Comment

#---- Webpage Handlers

class Home(Handler):    
    def get(self):
        paster = users.get_current_user()
        u = db.GqlQuery("SELECT * FROM Pasty ORDER BY Created DESC LIMIT 10")
        if u.count() < 1:
            u = None
        if paster:
            self.render('index.html', recent_pasties=u, logout_link=users.create_logout_url('/'), disable=not bool(paster))
        else:
            self.render('index.html', recent_pasties=u, login_link=users.create_login_url(self.request.uri), disable=not bool(paster))

    def post(self):
        paster = users.get_current_user()
        name    = self.request.get('name').strip() or "Anonymous"
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
            u2 = memcache.get("comments:%s" % id)
            if u2 is None:
                u2 = db.GqlQuery("SELECT * FROM Comment WHERE PostId=:1 ORDER BY Created", id)
                u2 = u2.fetch(None)
                if not memcache.add("comments:" + id, u2):
                    logging.error('Memcache set failed, while trying to add comments:' + id)
            self.render("view_pasty.html", pasty=u, is_owner=is_owner, logged_in=bool(paster),
                        comments=reversed(u2), paster=paster)

class Delete_Comment(Handler):
    def get(self, key):
        paster = users.get_current_user()
        u = db.GqlQuery("SELECT * FROM Comment WHERE __key__ = KEY(:1)", key)
        
        if u.count() == 1:
            comment = u.fetch(1)[0]
            
            if comment.User == paster:
                comment_id = comment.key().id()
                post_id = comment.PostId
                # Let's first delete it from memcache
                comments = memcache.get('comments:'+post_id)
                logging.error("%s: %s" % (str(comments), comment.PostId))
                # we've got a list of comments now
                # lets delete what we need to
                removed_from_memcache = 0
                for com in comments:
                    if com.key().id() == comment_id:
                        comments.remove(com)
                        memcache.set("comments:"+post_id, comments)
                        removed_from_memcache = 1
                        break
                
                if removed_from_memcache == 0:
                    # Something's wrong with this memcache entry, lets clean it up
                    logging.error("Something wrong with comment:"+post_id+". I can't find the comment to delete. \
                                   Clearing this cache entry to prevent wrong output.")
                    memcache.delete('comments:'+post_id)

                # Now from the DB
                db.delete(u)

            else: # unauthorized
                self.error('403')
        else: # no such entry
            self.error('404')
    
class Add_Comments(Handler):
    def post(self, id, lineno):
        paster = users.get_current_user()
        comment = self.request.get('comment').strip()

        if paster == None or comment == '':
            self.error("203")
        elif not paster:
            self.error("403")
        else:
            u = Comment(User=paster, Content=comment, PostId=id, LineNo=lineno)
            u.put()
            m = memcache.get("comments:"+id)
            if m is None:
                logging.debug("Adding new memcache entry for comments:"+id)
                memcache.add("comments:"+id, [u])
            else:
                m.append(u)
                memcache.set("comments:"+id, m)
            self.redirect('/pasty/' + id)

class Pasty_Manipulation(Handler):
    
    #-- GET functions
    
    def delete_pasty(self, key):
        u = db.GqlQuery("SELECT * FROM Pasty WHERE __key__ = KEY('%s')" % (key))
        if u.count() == 1:
            pasty = u.fetch(1)[0]
            memcache.delete('comments:'+str(pasty.key().id()))
            db.delete(pasty)
            self.redirect('/')
        else:
            self.error('404')
    
    def edit_pasty(self, key):
        paster = users.get_current_user()
        u = db.GqlQuery("SELECT * FROM Pasty WHERE __key__ = KEY('%s')" % (key))
        if u.count() == 1:
            u = u.fetch(1)[0]
            if paster == u.User:
                self.render('edit_pasty.html', pasty=u)
            else:
                self.error('403')
        else:
            self.error('404')
        
    def get(self, action, key):
        actions = {'delete': self.delete_pasty,
                   'edit_pasty': self.edit_pasty }
        
        if action in actions:
                actions[action](key)
        else:
            self.error('404')
    
    #-- POST functions
    
    def edit_pasty_post(self, key):
        paster  = users.get_current_user()
        name    = self.request.get('name').strip() or "Anonymous"
        content = self.request.get('content').strip()

        if name and content:
            u = db.GqlQuery("SELECT * FROM Pasty WHERE __key__ = KEY('%s')" % (key))
            if u.count() == 1:
                u = u.fetch(1)[0]
                if u.User == paster:
                    u.Name = name
                    u.Content = content
                    u.put()
                    self.redirect('/pasty/%s' % u.key().id())
                else:
                    self.error('403')
            else:
                self.error('203')
        else:
            self.redirect('/pasty/edit_pasty/'+key)
            
    def post(self, action, key):
        actions = {'edit_pasty': self.edit_pasty_post}

        if action in actions:
                actions[action](key)
        else:
            self.error('404')

app = webapp2.WSGIApplication([(r'/'               , Home),
                               (r'/pasty/([0-9]+)',  View_Pasty),
                               (r'/pasty/(.+)/(.+)', Pasty_Manipulation),
                               (r'/add_comment/([0-9]+)/([0-9]+)', Add_Comments),
                               (r'/comments/delete/(.+)', Delete_Comment)], debug=True)