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

from src.bvtlib import mongodb

db = mongodb.get_autotest()


class Point:
    def __init__(self, build, time):
        self.build = build
        self.time = time
        self.values = []
    
    def getaverage(self):
        return sum(self.values, 0.0) / len(self.values)
    average = property(getaverage)
    
    def __cmp__(self, other):
        return cmp(self.time, other.time)


def get_boot_times():
    """
    data = [
        (dut_0, [(build_0, time_0), ..., (build_n, time_n)]),
        ...,
        (dut_n, [(build_0, time_0), ..., (build_n, time_n)]),
    ]
    """
    # Divide the boot times by dut and by build id
    dut_boot_times = {}
    for t in db.boot_time.find():
        dut, time, build, value = t['dut'], t['time'], t['build'], t['value']
        if dut not in dut_boot_times:
            dut_boot_times[dut] = {}
        
        if build not in dut_boot_times[dut]:
            dut_boot_times[dut][build] = Point(build, time)
        
        dut_boot_times[dut][build].values.append(value)
    
    # Sort the points by time
    data = []
    for dut, build_points in dut_boot_times.iteritems():
        points = build_points.values()
        points.sort()
        dut_js_name = dut.replace('-', '_')
        data.append((dut, dut_js_name, points))
    
    return data
