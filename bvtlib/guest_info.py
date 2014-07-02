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

"""Provide information about guest"""

from bvtlib.run import run

def get_system_type(host, guest):
    out = run(['xec-vm', '-n', guest, 'get', 'os'], host=host)
    return out.strip()

def get_default_exec_method(host, guest):
    system = get_system_type(host, guest)
    if system == "windows":
        return "exec_daemon"
    elif system == "linux":
        return "ssh"
    else:
        raise Exception("No default exec method for %s" % system)

