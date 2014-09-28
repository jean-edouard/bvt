#! /usr/local/bin/python2.6
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

from src.bvtlib import testModules
import random
from time import sleep

def randF(func, priority):
    #func()
    return generateF(func.func_name, priority)

def generateF(desc, pr):
    if desc in ['hostHibernate', 'hostSleep', 'hostReboot', 'hostShutdown', 'dom0NetworkTest', 'vmNetworkTest', 'vmPowerOff', 'vmHibernate', 'vmShutdown', 'vmReboot']:
        box = []
        if pr == 1 or pr == 0: box.extend([testModules.hostHibernate, testModules.hostSleep,
                    testModules.vmHibernate, testModules.vmPowerOff])
        if pr == 2 or pr == 0: box.extend([testModules.hostReboot, 
                    testModules.vmReboot, testModules.vmNetworkTest,testModules.dom0NetworkTest])
        if pr == 3 or pr == 0: box.extend([testModules.hostShutdown,
                    testModules.vmShutdown])
        rfunc = random.sample(box,1)
        return rfunc[0]




