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

"""Simply test that we can see specific access points"""
from src.bvtlib.settings import ADVERTISED_ACCESS_POINTS, NO_WIFI_MACHINES
from src.bvtlib.exceptions import ExternalFailure
from src.bvtlib.run import run

class CannotSeeAccessPoints(ExternalFailure): 
    """Cannot detect known access point"""

class NoSiteAccessPointsKnown(ExternalFailure):
    """No access points are known for this site"""

def advertised_wireless(dut):
    """Check dut can see known access point"""
    look = dict( (x, 1) for x in ADVERTISED_ACCESS_POINTS)
    if look == {}:
        raise NoSiteAccessPointsKnown()
    for line in run(['nm-tool'], host=dut, split=True):
        if len(line) > 4 and line[3] == 'Freq':
            accesspoint = line[0][:-1]
            if accesspoint in look:
                print 'HEADLINE: seen access point', accesspoint
                del look[accesspoint]
    if look:
        raise CannotSeeAccessPoints(look, dut)

def entry_fn(dut):
    advertised_wireless(dut)

def desc():
    return 'Check that known access point is visible'
