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

def parse_xe_list(text):
    items = []
    for line in text.split('\n'):
        spl = line.split()
        if len(spl) < 2: continue
        if spl[0] == 'uuid': 
            item = dict(uuid=spl[-1])
            items.append( item)
        if len(spl) >= 4 and spl[2] in ['RO):', 'RW):']:
            item[spl[0]] = ' '.join(spl[3:])
    return items
