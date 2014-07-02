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

"""Run winsat benchmarks"""
from bvtlib.call_exec_daemon import run_via_exec_daemon
from bvtlib.exceptions import ExternalFailure
from re import search
from bvtlib.accelerate_graphics import have_accelerated_graphics
from bvtlib.wait_for_windows import wait_for_windows

class UnableToRecogniseWinSatOutput(ExternalFailure):
    """Unable to run WinSat"""

def d3d_tex(dut, guest):
    """Run Direct3D 9 texture benchmark"""
    vm_address = wait_for_windows(dut, guest)
    out = run_via_exec_daemon(['winsat', 'd3d', '-dx9', '-disp', 'on', '-tex'], 
                        host=vm_address, timeout=300)
    match = search('Direct3D ALU Performance\s+([0-9\.]+) F/s', out)
    if match is None:
        raise UnableToRecogniseWinSatOutput(out, vm_address, dut, guest)
    print 'INFO: fps', match.group(1)
    accelerated = have_accelerated_graphics(dut, guest, vm_address)

    print 'HEADLINE: %s Direct 3D winsat d3d -dx9 -tex fps=%s' % ( 
        'hardware accelerated' if accelerated else 'software emulated',
        match.group(1),)
    return float(match.group(1))

def futile(dut, guest, os_name, build, domlist):
    """Would the test work?"""
    try:
        vm_address = wait_for_windows(dut, guest, timeout=5)
        if not have_accelerated_graphics(dut, guest, vm_address):
            return 'no accelerated graphics'
    except Exception, exc:
        return 'unable to contact windows'

TEST_CASES = [
    { 'description': 'Winsat Direct X 9 texture benchmark on $(OS_NAME)',
      'command_line_options': ['--graphics-winsat'],
      'futile': futile, 
      'operating_systems': ['win7', 'win7_sp1', 'win7x64', 'win7x64_sp1',
                            'vista'],
      'bvt':True, 'function': d3d_tex, 'trigger' : 'VM ready',
      'arguments' : [('dut', '$(DUT)'), ('guest', '$(GUEST)')]}]

                     
