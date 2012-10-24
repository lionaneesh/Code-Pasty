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

from google.appengine.ext import db

#-- The Pasty Database Model

# Stores all the pasties.

class Pasty(db.Model):
    Name          = db.StringProperty(required = True)
    Content       = db.TextProperty(required = True)
    User          = db.UserProperty(required = True)
    Last_Modified = db.DateTimeProperty(auto_now = True)
    Comments      = db.TextProperty(required = True)