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

"""Update build information"""
from bvtlib.mongodb import get_track, get_autotest

def set_build_information(build, changes):
    """make changes to records about build"""
    track = get_track()
    autotest = get_autotest()
    change = False
    builddoc = autotest.builds.find_one({'_id':build})
    if builddoc:
        for field in changes:
            if changes[field] != builddoc.get(field):
                print 'SET_BUILD: field', field, 'changed on', build
                change = True
    if change:
        autotest.builds.update({'_id':build}, {'$set':changes})
        track.updates.save({'build': build, 'action' : 'new build information'})
