#! /usr/bin/env python
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

import logging as log
from sys import argv, exit

from xc.bus import dbus_loop
from xc.synchronizer import Register, Deregister

ACTIONS = {}
for a in [Register, Deregister]:
    ACTIONS[a.__name__.lower()] = a

def usage(msg):
    print '\n[ERROR] %s\n' % msg
    print 'Usage: %s ACTION [args]\n' % argv[0]
    print 'ACTIONs:'
    for name, a in ACTIONS.iteritems():
        print '  * %s: %s' % (name, a.__doc__)
    exit(1)


if __name__ == '__main__':
    log.basicConfig(level=log.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')
    
    if len(argv) < 2:
        usage('Not enough arguments, you should specify the desired action')
    
    action = argv[1]
    if action not in ACTIONS.keys():
        usage('Unknown action: %s' % action)
    
    try:
        actor = ACTIONS[action](argv[2:])
    except Exception, e:
        usage(str(e))
    
    dbus_loop(actor)
