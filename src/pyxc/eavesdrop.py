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

# This is in a separate script because all the connections established before
# the dbus reloading with the new configuration will maintain the old policy
from optparse import OptionParser
import logging as log

from xc.bus import DBusConfig


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-a", "--action", default="allow",
                      help="allow/disallow")
    (options, args) = parser.parse_args()
    
    log.basicConfig(level=log.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
    
    config = DBusConfig()
    
    if options.action == 'allow':
        config.allow_eavesdrop()
    
    elif options.action == 'disallow':
        config.disallow_eavesdrop()
