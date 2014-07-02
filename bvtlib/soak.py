#! /scratch/autotest_python/bin/python
#
# Copyright (c) 2014 Citrix Systems, Inc.
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

from bvtlib.network_test import network_test
from bvtlib import get_build
from bvtlib.set_pxe_build import set_pxe_build
from bvtlib.power_control import set_pxe_s0, set_s5
from bvtlib.get_build import get_build
from bvtlib.wait_to_come_up import wait_to_come_up
import optparse


def soak_up( dut):
    """Turn on dut"""
    set_pxe_build(dut, action='boot')
    set_pxe_s0(dut)
    wait_to_come_up(dut)
    build = get_build(dut)
    print 'SOAK:', 'found build', build 
    print 'SOAK:', 'making sure dom0 is okay by testing networking' 
    network_test(dut, 'all')
    print 'SOAK:', 'in power state s0' 


def soak_down( dut, target='s5', who='all'):
    """Turn off dut"""
    assert target == 's5'
    print 'SOAK:', 'going to s5', dut
    set_s5(dut)
    set_pxe_build(dut, action='boot')
    print 'SOAK:', 'in s5', dut

TEST_CASES = [
    {'description':'Soak test $(SOAK_POWER_LEVEL)', 'trigger':'soakdown',
     'options_predicate' : lambda options: options.soak_power_level,
     'function' : soak_down, 
     'arguments' : [('dut', '$(DUT)'), ('target', '$(SOAK_POWER_LEVEL)')]},
    {'description':'Soak up', 'trigger' : 'soakup',
     'options_predicate' : lambda options: options.soak_power_level,
     'function' : soak_up, 'arguments' : [('dut', '$(DUT)')]}]
