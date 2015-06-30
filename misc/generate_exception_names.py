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

"""Fill in the exception keys in the results databases"""
from bvtlib.mongodb import get_autotest
from re import match

mdb = get_autotest()
for result in mdb.results.find({'exception':{'$exists':0}, 'failure':{'$exists':1, '$ne':''}}).sort([('end_time',-1)]):
    assert 'exception' not in result
    if result['failure'] is not None:
        m = match('(\w+)\(', result['failure'])
        if m:
            print '\t', repr(m.group(1))
            result['exception'] = m.group(1)
            mdb.results.save(result)



    
