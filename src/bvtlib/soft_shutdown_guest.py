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

"""Shutdown system using system-specific method"""
from src.bvtlib.call_exec_daemon import call_exec_daemon
from src.bvtlib.run import run
from src.bvtlib.domains import find_domain, domain_address
from src.bvtlib.time_limit import TimeoutError
from time import time, sleep

DEFAULT_SHUTDOWN_TIMEOUT = 600

def is_stopped(host, guest):
    domain = find_domain(host, guest)
    if domain['status'] == 'stopped': 
        return True
    return False

def wait_for_shutdown(host, guest, timeout=DEFAULT_SHUTDOWN_TIMEOUT):
    start_time = time()
    while time() - start_time < timeout:
        domain = find_domain(host, guest)
        if domain['status'] == 'stopped': 
            return True
        sleep(5)
    raise TimeoutError()

def soft_shutdown_guest(host, guest, timeout=DEFAULT_SHUTDOWN_TIMEOUT, method="exec_daemon"):
    """Shutdown guest using platform-specific method"""
    if is_stopped(host, guest):
        return True
    vm_address = domain_address(host, guest, timeout=5)
    if method == "exec_daemon":
        call_exec_daemon('shutdown', host=vm_address, timeout=20)
    elif method == "ssh":
        run(['shutdown', '-h', 'now'], host=vm_address, timeout=20, check_host_key=False)
    else:
        raise Exception("Unknown method %s" % method)
    wait_for_shutdown(host, guest, timeout=timeout)
    return True

