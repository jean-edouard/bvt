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

"""Check partition table alignment"""
from src.bvtlib.exceptions import ExternalFailure
from src.bvtlib.run import run
from src.bvtlib.settings import MISALIGNED_PARTITIONS_DONTCARE_REGEXP
from re import compile

FDISK_COLUMNS = ['Device', 'Boot', 'Start', 'End', 'Blocks', 'Id', 'System']

class MisalignedPartition(ExternalFailure):
    """Show details of an incorrectly aligned partition"""

class NoPartitionsParsed(ExternalFailure):
    """Partition table line could not be parsed"""

def partition_table_test(dut):
    """Check all partitions start on 4K alignment"""
    out = run(['fdisk', '-l', '-u'], host=dut, split=True)
    print 'PARTITION_TABLE:', repr(out)
    prev = None
    work = False
    MISALIGNED_PARTITIONS_DONTCARE = compile(MISALIGNED_PARTITIONS_DONTCARE_REGEXP)
    for spl in out:
        if len(spl) == len(FDISK_COLUMNS) and prev == FDISK_COLUMNS:
            data = dict(zip(FDISK_COLUMNS, spl))
            if MISALIGNED_PARTITIONS_DONTCARE.match(data['Device']):
                print 'INFO: ignored dontcare parititon', data
                continue
            start_bytes = (int(data['Start'])) * 512
            alignment = start_bytes % 4096
            if alignment:
                raise MisalignedPartition(data, dut)
            print 'INFO: accepted partition', data
            work = True
        prev = spl
    if not work:
        raise NoPartitionsParsed(dut, out)

def futile(dut, guest, os_name, build, domlist):
    """Do not run this test on dodo since it fails due to 
    an old partition table"""
    if dut == 'dodo':
        return 'weird partition table on dodo'

def entry_fn(dut):
    partition_table_test(dut)

def desc():
    return 'Check partitions are 4KB aligned'
