#
# Copyright (c) 2011 Citrix Systems, Inc.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

from pymongo import Connection, DESCENDING, ASCENDING

from bvtlib.settings import MONGODB_HOST, MONGODB_DATABASE, TRACK_DATABASE, LOGGING_DATABASE
CONNECTIONS = {}

def open(name):
    cur = CONNECTIONS.get(name)
    if name not in CONNECTIONS:
        CONNECTIONS[name] = Connection(MONGODB_HOST)[name]
    return CONNECTIONS[name]
    
def get_autotest():
    return open(MONGODB_DATABASE)

def get_track():
    return open(TRACK_DATABASE)

def get_logging():
    return open(LOGGING_DATABASE)
