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

"""Code to make the tools iso available"""
from src.bvtlib.run import run

def set_iso(dut, domain, disk_path):
    """Attach disk_path as a disk to domain"""
    disk_uuid = run(['xec-vm', '-u', domain['uuid'], 'add-disk'], 
                    word_split=True, host=dut)[0]
    print 'INFO: disk', disk_uuid, 'path', disk_path
    run(['xec', '-o', disk_uuid, 'set', 'phys-path', disk_path], host=dut)
    run(['xec', '-o', disk_uuid, 'set', 'phys-type', 'file'], host=dut)
    run(['xec', '-o', disk_uuid, 'set', 'devtype', 'cdrom'], host=dut)
