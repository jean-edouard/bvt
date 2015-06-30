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

"""Repeatedly try to ssh into machine"""
from src.bvtlib.time_limit import TimeoutError, time_limit
from src.bvtlib.run import run, isfile
from src.bvtlib.retry import retry
from src.bvtlib import mongodb
from time import sleep

class InstallerRunning(Exception):
    """We found the installer running on a test machine"""

def is_installer_running(host, timeout=5):
    """Is the installer running with ssh open on host?"""
    return isfile('/etc/xenclient-host-installer', host=host, timeout=timeout)

def check_up(host, installer_okay=False):
    """Check if host is up in XenClient (rather than the installer)"""
    try:
        out = run(['uptime'], host=host, timeout=30)
    except TimeoutError:
        print 'WAIT_TO_COME_UP:', host, 'could not be contacted'
        raise
    if is_installer_running(host):
        print 'WAIT_TO_COME_UP:', host, 'is up in installer'
        if not installer_okay:
            raise InstallerRunning(host)
    else:
        print 'WAIT_TO_COME_UP:', host, 'is up as platform'
    return out

def wait_to_go_down(host, timeout=120, pace=1):
    """Check that host goes down within timeout"""
    with time_limit(timeout, description='wait for '+host+' to go down'):
        while 1:
            try:
                check_up(host)
            except Exception, exc:
                print 'CHECK_DOWN: got exception', repr(exc), \
                    'so assuming host down'
                break
            else:
                print 'CHECK_DOWN:', host, 'is still up'
            sleep(pace)

def wait_to_come_up(host, timeout=120, installer_okay=False):
    """Return once host is up and responding to ssh, or thrown
    an exception on timeout"""
    
    if installer_okay:
        mdb = mongodb.get_autotest()
        dut_doc = mdb.duts.find_one({'name': host})
        if dut_doc.get('num-nics'):
            if dut_doc['num-nics'] == 2: 
                host = host+'-amt' 
    out = retry(lambda: check_up(host, installer_okay),
          description='run true on '+host+' to see if it is up',
          timeout=timeout)

    print 'WAIT_TO_COME_UP:', host, 'responded with up time', out[:-1]

