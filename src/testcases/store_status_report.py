#
# Copyright (c) 2014 Citrix Systems, Inc.
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

"""Archive platform or installer status report on artifact filter"""
from src.bvtlib import mongodb
from src.bvtlib.store_artifact import store_client_artifact
from src.bvtlib.run import run, readfile, TimeoutError, SubprocessError
from src.bvtlib.wait_to_come_up import wait_to_come_up
from src.bvtlib.set_pxe_build import set_pxe_build
from src.bvtlib.power_control import power_cycle, set_pxe_s0, NoPowerControl

POSTFIX = '.report.tar.bz2'
MAGIC = ['Writing','tarball']

#Simplified version of store_status_report
def get_status_report(dut, port=22, command = 'status-tool', 
                        reason='unknown', try_installer=False,
                        label='-platform'):
    """Use status-tool on XT box to generate a status report and rsync it back to 
        BVT machine for inspection"""

    try:
        wait_to_come_up(dut, timeout=10)
        out, exitcode = run(['/usr/bin/'+command], timeout=600, host=dut, ignore_failure=True)
        print 'STATUS_REPORT: made status report reason', reason, 'exit code', \
            exitcode
        out2 = out[out.find(' '.join(MAGIC)):]
        spl = out2.split()
        if spl[:2] != MAGIC  or len(spl)!=4:
            print 'STATUS_REPORT: unexpected status-tool output', out
        else:
            report = spl[-2]
            print 'STATUS_REPORT: downloading', report
            report_loc = store_client_artifact(dut, report, 'status-reports', 
                                               label+POSTFIX)
            print 'INFO: created status report', report_loc
            return (report_loc)
    except (SubprocessError, TimeoutError):
        print 'INFO: unable to connect'
        raise 

def store_status_report(dut, port=22, command = 'status-tool', 
                        reason='unknown', try_installer=False,
                        label='-platform'):
    """Make a status report and store it on the artifacts server"""
    print 'INFO: getting status report from', dut, 'reason '+str(reason)
    set_pxe_build( dut, action='boot')
    try:
        set_pxe_s0(dut)
    except NoPowerControl:
        pass
    try:
        wait_to_come_up(dut, timeout=10)
        out, exitcode = run(['/usr/bin/'+command], timeout=600, host=dut, ignore_failure=True)
        
        print 'STATUS_REPORT: made status report reason', reason, 'exit code', \
            exitcode
        out2 = out[out.find(' '.join(MAGIC)):]
        spl = out2.split()
        if spl[:2] != MAGIC  or len(spl)!=4:
            print 'STATUS_REPORT: unexpected status-tool output', out
        else:
            report = spl[-2]
            print 'STATUS_REPORT: downloading', report
            report_loc = store_client_artifact(dut, report, 'status-reports', 
                                               label+POSTFIX)
            print 'INFO: created status report', report_loc
            set_pxe_build( dut, action='boot')

            return (report_loc)
    except (SubprocessError, TimeoutError):
        print 'INFO: unable to connect'
        if try_installer:
            print 'INFO: trying installer status report'
            try:
                return store_installer_status_report(
                    dut, reason='unable to connect when geting '+reason)
            finally:
                set_pxe_build( dut, None, 'boot')
        else:
            raise

def store_installer_status_report(dut, reason='unknown'):
    """Make a status report using the installer"""
    build_doc = mongodb.get_autotest().builds.find_one(
        {'branch':'master'}, sort=[('build_time', mongodb.DESCENDING)])
    print 'STATUS_REPORT: chose installer of %(_id)s on %(branch)s' % build_doc
    default_build = str(build_doc['_id'])
    print 'STATUS_REPORT: getting installer status report reason', reason
    set_pxe_build(dut, default_build, 'ssh')
    power_cycle(dut, pxe=True)
    wait_to_come_up(dut, timeout=600)
    print 'STAUTS_REPORT: connected to port 22'
    return store_status_report( dut, port=22,
                                command='status-report', reason=reason,
                                try_installer=False, label='-installer')

def entry_fn(dut, reason, mode):
    if mode == 'diagnostic':
        get_status_report(dut, reason)
    if mode == 'installer':
        store_installer_status_report(dut, reason)

def desc():
    return 'Store a status report.'
