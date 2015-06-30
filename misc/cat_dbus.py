#! /scratch/autotest_python/bin/python
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

from sys import argv, exit

from bvtlib.dbus_log_parser import KNOWN_EVENTS, parse_log

if __name__ == '__main__':
    if len(argv)<2:
        print 'Usage: ./cat_dbus.py LOG_BASE [EVENT]'
        print '    LOG_BASE: the path to the log without extension'
        print '    EVENT   : optional event parsers. Available: %s' % KNOWN_EVENTS.keys()
        exit(1)
    
    event = None if len(argv) < 3 else argv[2]
    parse_log(argv[1], event)
