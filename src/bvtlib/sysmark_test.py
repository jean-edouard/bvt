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

from src.bvtlib import connection, install_tools, boot_monitor, have_driver, retry
from src.bvtlib import autoit_generator, test_failure, sleep, connect_to_exec_daemon

class InsufficientReboots(Exception): pass


def exists(con, filename):
    rc2,o,_ = con.launch('dir "'+filename+'"')
    print 'dir code',rc2,'output',repr(o)
    return (  rc2 == 0 and filename.split('\\')[-1]  in o)

def check_boots(n, bm):
    
    def fn():
        bm.get_boot_time()
        status = str(bm.get_number_of_boots())+' boots, want '+str(n)
        print 'INFO:',status
        if bm.get_number_of_boots() < n: raise InsufficientReboots(status)
    return fn
    


def sysmark_test( dut, domain, cd_drive='D'):
    con = (connect_to_exec_daemon.connect_to_windows_guest(
            session, dut,domain))
    
    iso = "/storage/isos/sysmark.iso"
    with connection.connect(host=dut, user='root') as sh_dut:    
        rc, _, _ = sh_dut.launch('ls '+iso)
        if rc != 0:
            sh_dut.verified_launch('wget http://autotest/sysmark_2004_se.iso -O '+iso,
                                         timeout=3600)
        if not exists(con, cd_drive+':\\setup.boot'):
            sh_dut.verified_launch(
                "db-cmd write /vm/"+domain['uuid']+"/config/disk/0/path "+iso)
            install_tools.wait_for_reboot( sh_dut, uuid=domain['uuid'],
                                                name=domain['name'])
    # Make the execdaemon actually start up again (sm2004se disables all
    # entries in the Run part of the registry)
    sed = r"c:\execdaemon.cmd"
    con.proxy.callRemote(
        'createFile', "C:\\docume~1\\admini~1\\startm~1\\Programs\\Startup"
                      "\\execdaemon.bat", sed)
    if  exists(con, r'C:\sm2004se\xen.iss'):
        print 'INFO: already have sm2004se management material'
    else:
        con.proxy.callRemote('unpackTarball', 
                                   'http://autotest/bin/sm2004se.tgz', 'C:\\')
        print 'INFO: unpacked sm2004se.tgz'
    
    if have_driver.have_driver(con, 'MEDIA' ,'Virtual Audio Cable'):
        print 'INFO: have virtual audio cable driver already installed'
    else:
        con.proxy.callRemote(
            'unpackTarball',
            'http://autotest.cam.xci-test.com/bin/devcon.tar.gz','C:\\')
        print 'INFO: unpacked devcon'
        con.verified_launch(
            'C:\\devcon\\i386\\devcon.exe install C:\\sm2004se\\vac\\vrtaucbl.inf '+
            'EuMusDesign_VAC_WDM', timeout=600)
    
    sysmd = r'C:\Program Files\BAPCo\SYSMark 2004 SE'
    sysmgrd = sysmd + r'\Benchmgr'
    sysmgrf = 'Sysmgr.exe'
    sysmgr = sysmgrd + '\\' + sysmgrf
    if not exists(con,sysmgr):
        bootmon = boot_monitor.BootMonitor(con)
        bootmon.get_first_boot_time()
        def record(f): test_failure.log_failure( f, 'installing sysmark')
        print 'INFO: waiting for quiescence before installing sysmark'
        sleep.sleep(300)
        print 'INFO: starting install'
        con.launch(
            cd_drive+':\\setup.exe -s -f1C:\\sm2004se\\xen.iss', timeout=3600).addErrback(
              record)
        retry.retry(
            check_boots(2, bootmon), 
            description='wait for Sysmark to be installed, indicated by reboots', 
            timeout=60*60*24, catch=[InsufficientReboots])
    else: assert 0
    assert exists(con,sysmgr)
    target_exe = (autoit_generator.compile(con, 'set_keyboard', 
                                                 autoit_generator.set_keyboard_layout))
    con.verified_launch(target_exe)
    bootmonr = boot_monitor.BootMonitor(con)
    con.launch('"'+sysmgr+'" STDSUITE=1 PROJNAME=XenRT')
    retry.retry(check_boots(3, bootmonr), 
                     description='wait for Sysmark to complete, indicated by reboots', 
                     timeout=60*60*6, catch=[InsufficientReboots])
    report = con.proxy.callRemote('readFile', sysmgrd+'\\Report\\XENRT.WMR')
    for line in report.split('\n'):
        print 'INFO: report',line
