#! /scratch/autotest_python/bin/python
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

from sys import argv
from bvtlib.ensure import ensure
from bvtlib.network_test import network_test_guest
from bvtlib.windows_transitions import hibernate_windows
from bvtlib.start_vm import start_vm

dut = argv[1]
guests = argv[2:]
addresses = {}
for guest in guests:
    addresses[guest] = ensure(dut, guest, busy_stop=False)

for i in xrange(100000):
    print
    print
    print 'loop', i
    print
    for guest in guests:
        network_test_guest(dut, guest, description='test networking in '+guest)
    for guest in guests:
        hibernate_windows(addresses[guest])
    for guest in guests:
        start_vm(dut, guest)

        

