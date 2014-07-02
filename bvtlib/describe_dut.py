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

"""Return a string describing a dut"""
from bvtlib.mongodb import get_autotest
from bvtlib.settings import DUT_FIELDS

def pretty(field, value):
    if field == 'memory':
        return '%dMB' % (value/(1024*1024))
    if field == 'make':
        return value.replace(' Inc.', '')
    return value

def describe_dut(dut):
    """Return a string describing a dut"""
    dutdoc = get_autotest().duts.find_one({'name':dut})
    if dutdoc is None:
        return dut
    attrs = [pretty(f, dutdoc[f]) for f in DUT_FIELDS if f in dutdoc]
    out = dut
    if attrs:
        out += ' ('+ (' '.join(attrs))+')'
    return out
