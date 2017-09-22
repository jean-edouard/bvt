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

"""Get build installed on dut"""
from src.bvtlib.exceptions import ExternalFailure
from src.bvtlib.run import run, SubprocessError
from src.bvtlib.time_limit import TimeoutError
from src.bvtlib.retry import retry
from src.bvtlib.wait_to_come_up import wait_to_come_up, InstallerRunning
from re import search
from src.bvtlib import mongodb

class UnrecongisedEtcIssue(ExternalFailure):  
    """Bad content in /etc/issue"""

class UnableToDetermineBuild(ExternalFailure):
    """Uunable to determine the currnet build"""

def try_get_build_number_branch(dut, timeout=60):
    """Get build number and branch running on dut or throw exception"""
    print 'GETBUILD: connect to', dut
    wait_to_come_up(dut, timeout=timeout, installer_okay=False)
    issue = run(['cat','/etc/issue'], timeout=timeout, host=dut)
    branch = None
    matchbr = search(r'build_branch\s*=\s*([0-9a-zA-Z\-]+)', issue)
    match = search(r'build\s*=\s*([0-9a-zA-Z\-]+)', issue)
    if match is None:
        raise UnrecongisedEtcIssue(issue)
    if matchbr:
        branch = matchbr.group(1)
    else: 
        branch = 'master'
    print 'GETBUILD: detected build', match.group(1), branch, 'on', dut
    return match.group(1), branch
    
def get_build_number_branch(dut, timeout=60):
    """Get build number and branch running on 'dut' or None if that cannot be determined"""
    print 'GETBUILD: determining the Xen Client version installed on', dut
    try:
        build = retry(lambda: try_get_build_number_branch(dut, timeout=timeout),
              timeout=timeout,
              description='get build on '+dut)
    except (TimeoutError, SubprocessError, InstallerRunning), exc:
        print 'GETBUILD: error', repr(exc)
        return
    else:
        return build

def get_build(dut, timeout=60):
    """Use Mongo to determine the build on dut"""
    mdb = mongodb.get_autotest()
    dut_doc = mdb.duts.find_one({'name':dut})
    return dut_doc['build']

def try_get_build(dut, timeout=60):
    """Return build on dut or throw exception"""
    build = get_build(dut, timeout=timeout)
    if build is None:
        raise UnableToDetermineBuild(dut)
    return build

