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

"""Wait for guest (Windows or Linux) to come up"""

from bvtlib.run import run
from bvtlib.domains import domain_address
from bvtlib.domains import name_split
from bvtlib.retry import retry
from bvtlib.call_exec_daemon import call_exec_daemon
from bvtlib.guest_info import get_default_exec_method
from socket import error
from time import time, sleep

class UnableToContactGuestService(Exception):
    """We were not able to contact the guest sytem service"""

class SystemUnstable(Exception):
    """Guest system would not stay up for the specified period"""

class SystemUnreachable(Exception):
    """Guest system could not be contacted in specified period"""

class SystemStoppedWhileWaitingForSystem(Exception):
    """Guest system was stopped while waiting for it to respond"""

def ensure_stable(vm_address, interval, timeout=600, description=None, method="exec_daemon"):
    """Ensure that vm_address is continuaully up for interval"""
    assert method in ['exec_daemon', "ssh"]
    last_down = time()
    start = time()
    last_out = time()
    reached = False
    while 1:
        delta = time() - last_down
        run_time = time() - start
        if delta > interval:
            print 'HEADLINE: VM at', vm_address, description, 'has been stable for', delta
            return
        if run_time > timeout:
            args = (time() - last_out, timeout, vm_address, description)
            if reached:
                raise SystemUnstable(*args)
            else:
                raise SystemUnreachable(*args)
        try:
            if method == "exec_daemon":
                call_exec_daemon('windowsVersion', [], host=vm_address, timeout=60)
            elif method == "ssh":
                run(['true'], host=vm_address, timeout=60, check_host_key=False)
            else:
                raise Exception("Unkonwn method %s" % method)
        except Exception, exc:
            last_down = time()
        else:
            delta = time() - last_down
            print 'WAIT_FOR_SYSTEM: stable for', delta, 'of', interval, 'seconds'
            last_out = time()
            reached = True
        sleep(1)

def wait_for_guest(host, guest, method=None, timeout=600):
    """Return address for guest on host, checking that it is responding
    and retrying as necessary"""
    if method is None:
        method = get_default_exec_method(host, guest)
    assert method in ['exec_daemon', "ssh"]
    print 'WAIT_FOR_SYSTEM: contacting', guest, 'using', method
    _, name = name_split(guest)
    start = time()
    run(['xec-vm', '-n', name, 'switch'], host=host)
    def check_running():
        """check VM is running"""
        count = 0
        while(1):
            out = run(['xec-vm', '-n', name, 'get', 'state'], word_split=True, host=host)
            print 'WAIT_FOR_SYSTEM: VM', name, 'state', out[0]
            if out[0] == 'stopped':
                if count > 4: raise SystemStoppedWhileWaitingForSystem(out, guest, host)
                else: count+=1
                sleep(2)
            else: break

    def get_address():
        """get address for VM """
        check_running()
        return domain_address(host, guest, timeout=5)

    address = retry(get_address, 'get %s address on %s' % (guest, host),
                    timeout=timeout, propagate=[SystemStoppedWhileWaitingForSystem])
    delta = time() - start
    rtimeout = max(30, int(timeout - delta))
    print 'WAIT_FOR_SYSTEM: remainining timeout', rtimeout, 'of', timeout
    def check_windows_version():
        """Check that VM is still running"""
        check_running()
        out = call_exec_daemon('windowsVersion', [], host=address, timeout=60)
        print 'WAIT_FOR_SYSTEM: windows version returned', out
    def check_ssh_access():
        """Check that VM is available over ssh"""
        check_running()
        run(['echo', 'test succeeded'], host=address, timeout=60, check_host_key=False)
        print 'WAIT_FOR_SYSTEM: ssh command execution succeeded'
    if method == "exec_daemon":
        try:
            ver = retry(check_windows_version,
                        description='run windowsVersion on '+host+' '+guest,
                        timeout=rtimeout,
                        propagate=[SystemStoppedWhileWaitingForSystem])
        except error:
            raise UnableToContactGuestService(host, guest, timeout, error)
        print 'WAIT_FOR_SYSTEM:', guest, 'on', host, \
            'replied with windows version', ver, 'from address', address
    elif method == "ssh":
        retry(check_ssh_access,
          description='run ssh check on '+host+' '+guest,
          timeout=rtimeout,
          propagate=[SystemStoppedWhileWaitingForSystem])
        print 'WAIT_FOR_SYSTEM:', guest, 'on', host, \
            'ssh test succeed on', address
    return address
