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

"""Wait for windows to come up"""
from src.bvtlib.wait_for_guest import wait_for_guest
from src.bvtlib.run import run
from src.bvtlib.time_limit import TimeoutError, time_limit
from src.bvtlib.call_exec_daemon import call_exec_daemon
from socket import error
from time import sleep

# backward compat:
from wait_for_guest import ensure_stable

def wait_for_windows(host, guest, timeout=600):
    return wait_for_guest(host, guest, "exec_daemon", timeout)

def is_windows_up(host, timeout=60):
    """Return true if windows is up on vm_address"""
    try:
        call_exec_daemon('windowsVersion', [], host=host, timeout=timeout)
    except (TimeoutError, error):
        return False 
    else: return True

def guest_status(dut, guest, timeout=5):
    """Check if VM has stopped"""
    stat = run(['xec-vm', '-n', guest, 'get', 'state'], word_split=True, host=dut)
    return stat[0]

def wait_for_guest_state(dut, guest, predicate, timeout=120, pace=1):
    """Wait for guest state to fulfill predicate"""
    with time_limit(timeout, description='wait for '+guest+' to go down'):
        while 1:
            status = guest_status(dut, guest)
            print 'INFO: VM', guest, 'status', status
            if predicate(status):
                break
            sleep(pace)

def wait_for_guest_to_go_down(dut, guest, timeout=120, pace=1):
    """Check that guest goes down within timeout"""
    wait_for_guest_state(dut, guest, (lambda x: x == 'stopped'), timeout, pace)


def wait_for_guest_to_start(dut, guest, timeout=120, pace=1):
    """Check that guest goes down within timeout"""
    wait_for_guest_state(dut, guest, (lambda x: x == 'running'), timeout, pace)
