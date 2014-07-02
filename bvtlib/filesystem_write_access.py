#
# Copyright (c) 2012 Citrix Systems, Inc.
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

"""Get read write access to a filesystem temporarily."""
from bvtlib.run import run

class FilesystemWriteAccess:
    """Get access to filesystem"""
    def __init__(self, dut, filesystem):
        self.filesystem = filesystem
        self.dut = dut
        self.readonly = False
    def __enter__(self):
        for mount in run(['cat', '/proc/mounts'], host=self.dut, split=True):
            if len(mount) == 6 and mount[1] == self.filesystem:
                self.readonly = 'ro' in mount[3].split(',')
        if self.readonly:
            run(['mount', '-orw,remount', self.filesystem], host=self.dut)
    def __exit__(self, *_):
        if self.readonly:
            run(['mount', '-oro,remount', self.filesystem], host=self.dut)
