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

"""Check dut name is valid, or exit"""
from src.bvtlib import mongodb
from src.bvtlib.run import run, SubprocessError
from sys import exit

def validate_dut_name(dut):
    """Check dut is a valid test device name"""
    mdb = mongodb.get_autotest()
    if mdb.duts.find_one({'name':dut}) is None:
        try:
            run(['host', dut], timeout=2)
        except SubprocessError:
            print 'ERROR: unable to determine DNS record for DUT ' + \
                dut + '; did you spell it right?'
            exit(1)
        else:
            print 'INFO: confirmed DNS record for', dut
        mdb.duts.save({'name':dut, '_id':dut})
    dut_document = mdb.duts.find_one({'name':dut})
    if dut_document.get('mem') is None:
        try:
            out = run(['xenops', 'physinfo'], host=dut, split=True)
            for spl in out:
                if spl[:1] == ['total_pages'] and len(spl) == 5:
                    upd = {'$set' : {'mem':int(spl[-2][1:])}}
                    mdb.duts.update({'name':dut}, upd)
                    
        except SubprocessError, exc:
            print 'WARNING: unable to discover memory in', dut, exc
        
