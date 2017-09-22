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

from datetime import datetime
from src.bvtlib.exceptions import ExternalFailure
from src.bvtlib.run import run
from src.bvtlib.wait_to_come_up import wait_to_come_up, check_up
from src.bvtlib.time_limit import time_limit
from src.bvtlib.grep_dut_log import grep_dut_log

from time import sleep
# See: /manager/xenmgr/XenMgr/Expose/HostObject.hs
# The ":" distinguish the new format with uptime from the old one without
UI_READY = 'ui-ready notification:'

class NoTimestampForBuild(Exception):
    """Unable to find a timestamp for a build"""

def parse_sys_log(log):
    """Read the uptime until the ui-ready notification from the syslog"""
    boot_times = []
    for l in log.splitlines():
        if UI_READY in l:
            try:
                uptime_start = l.index(UI_READY) + len(UI_READY)
                uptime = float(l[uptime_start:].split()[0])
                boot_times.append(uptime)
            except Exception, _:
                print 'Error parsing uptime from: "%s"' % l.strip()
    
    return boot_times


def read_boot_time(dut, build):
    boot_times = None
    print 'INFO: sending reboot'
    # The first boot time after a fresh install is much slower than the following
    wait_to_come_up(dut)
    run(['reboot'], host=dut)
    with time_limit(600, 'wait for sync up event'):
        while 1:
            try:
                print 'INFO: checking if', dut, 'is still up'
                check_up(dut)
            except Exception, exc:
                print 'INFO:', dut, 'is down', exc
                break
            else:
                print 'INFO:', dut, 'still up'
                sleep(1)
                print
        while 1:
            wait_to_come_up(dut, timeout=1200)
            log = grep_dut_log(dut, '/var/log/messages', UI_READY)
            
            boot_times = parse_sys_log(log)
            print 'INFO: boot times:', ' '.join(['%.2f' % t for t in boot_times])
            if len(boot_times) >= 2:
                break
            sleep(5)
    if not boot_times:
        raise ExternalFailure('Unable to find ui-ready notification in the sys log')
    
def entry_fn(dut, build):
    read_boot_time(dut, build)

def desc():
    return 'Read the boot duration from syslog'
