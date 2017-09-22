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

from serverlib.tags import tr

def status_styling(params, content):
    """colour row appropriately"""
    if params.get('failure') or (
        params.get('unknown_failures',0)>0 or 
        params.get('product_problems', 0)>0):
        col = 'failure'
    elif params.get('passes',0)>0:
        col = 'pass'
    elif params.get('passes',0)>0:
        col = 'known'
    else:
        col = 'progress'
    attrs = {'class': col}
    return tr(**attrs)[content]
