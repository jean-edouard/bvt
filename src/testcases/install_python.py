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

from src.bvtlib.run import run
from os.path import split, abspath

def install_python(dut):
    _, ec= run(['python', '--version'], host=dut, ignore_failure=True)
    if ec == 0:
        print 'INFO: python already installed'
        return
    print 'INFO: copying python files on target'
    run(['scp', '-r', abspath(split(split(__file__)[0])[0])+'/pyxc', 'root@'+dut+':/root'])
    print 'INFO: launching python installer'
    run(['/root/pyxc/pysetup'], host=dut, timeout=3600)

def entry_fn(dut):
    install_python(dut)

def desc():
    return 'Install the python interpreter and the pyxc code'
