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

from bvtlib.mongodb import get_autotest

db = get_autotest()

# The boot_time "time" field stores the time of the build, not the time of the measure
for sample in db.boot_time.find():
    time = db.builds.find_one({'_id': sample['build']})['tag_time']
    db.boot_time.update({'_id':sample['_id']}, {'$set': {"time":time}})

# The "counts" collection are no longer used
for collection in db.collection_names():
    if collection.startswith('counts'):
        db[collection].drop()
