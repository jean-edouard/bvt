#! /scratch/autotest_python/bin/python
#
# Copyright (c) 2013 Citrix Systems, Inc.
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

from sys import argv
from bvtlib.mongodb import get_autotest, DESCENDING

if 'config' in argv:
    print 'graph_category autotest'
    print 'graph_title Automated tests'
    for kind in ['passes', 'failures', 'infrastructure_problems', 'unfinished']:
        print kind+'.type COUNTER'
        print kind+'.label '+kind+' per hour'
        print kind+'.draw ', 'AREA' if kind == 'passes' else 'STACK'
        print kind+'.cdef '+kind+',3600,*'
        print kind+'.max 1000'
    print 'passes.colour 00FF00'
    print 'failures.colour FF0000'
    print 'unfinished.colour 0000FF'
    print 'infrastructure_problems.colour FFC200'
    exit(0)

results = get_autotest().results
infrastructure = results.find({'infrastructure_problem':True, 'end_time':{'$exists':1}}).count()
print 'infrastructure_problems.value', infrastructure
passes = results.find({'failure':'', 'end_time':{'$exists':1}}).count()
print 'passes.value', passes
total = results.count()
unfinished = results.find({'end_time':{'$exists':0}}).count()
print 'unfinished.value', unfinished
print 'failures.value', total - passes - infrastructure - unfinished



