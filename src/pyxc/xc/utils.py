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

from subprocess import Popen, PIPE

def cmd(l, echo=False, check=False):
    if echo:
        print ' '.join(l)
    p = Popen(l, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    
    rc = p.returncode
    if check and rc != 0:
        print rc
        raise Exception("Error executing command")
    
    return out.strip(), err.strip(), rc # pylint: disable=E1103
