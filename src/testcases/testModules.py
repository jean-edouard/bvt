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

"""Run test modules on dom0 and guests"""
from src.bvtlib.exceptions import ExternalFailure
from src.bvtlib.retry import retry
from src.bvtlib.domains import list_vms, domain_address
from src.bvtlib.run import isfile, specify, SubprocessError
from src.bvtlib.call_exec_daemon import call_exec_daemon, run_via_exec_daemon
from src.bvtlib.wait_for_windows import wait_for_windows
from src.bvtlib.wait_to_come_up import wait_to_come_up, wait_to_go_down
from src.bvtlib.windows_transitions import wait_for_windows_to_come_up, wait_for_windows_to_go_down
from src.testcases.pxe_install_xc import pxe_install_xc
from src.testcases.install_guest import install_guest
from src.testcases.install_tools import install_tools
from src.bvtlib.tslib import find_guest_vms
from src.bvtlib.run import run
from src.bvtlib.tslib import log
from src.bvtlib import power_control, tslib, get_build, windows_transitions
from src.testcases import network_test
from socket import gethostname
from time import sleep

def installBuild(machine,vms,steps,build,test_path,caller):
    pxe_install_xc(machine, build) 

def upgradeBuild(machine,vms,steps,build,test_path,caller):
    build1, build2 = build.split(",")
    pxe_install_xc(machine, build1)
    install_guest(machine, vms)   
    sleep(30)
    install_tools(machine, vms)
    sleep(30)
    windows_transitions.vm_reboot_dom0(machine, vms)
 
    run(['xec', 'set', 'wallpaper', 'images/wallpaper/s6.png'],host=machine)

    tslib.forcepowerstate(machine, 'on', vms)
    domlist = domains.find_guest_vms(machine)
    for domain in domlist:
        run(['xec-vm', '-n', domain['name'], 'set', 'vcpus', '2'],host=machine)
        run(['xec-vm', '-n', domain['name'], 'set', 'slot', '7'],host=machine)
        run(['xec-vm', '-n', domain['name'], 'set', 'memory', '1048'],host=machine)
        network_test.network_test_guest(machine, domain['name'], 'guest network test')

    network_test.network_test_dom0(machine, 'dom0 network test')

    tslib.forcepowerstate(machine, 'off', vms)

    pxe_install_xc(machine, build2, upgrade=True)

    currentBuild = get_build.get_build(machine)
    if (currentBuild != build):  
           print "INFO: ERROR, UPRADE FAILED" 
    wall = run(['xec', 'get', 'wallpaper'],host=machine) 

    tslib.forcepowerstate(machine, 'on', vms)
    sleep(30)
    windows_transitions.vm_reboot_dom0(machine, vms) 
    for domain in domlist:
        vcpu = run(['xec-vm', '-n', domain['name'], 'get', 'vcpus'],host=machine) 
        slot = run(['xec-vm', '-n', domain['name'], 'get', 'slot'],host=machine) 
        memo = run(['xec-vm', '-n', domain['name'], 'get', 'memory'],host=machine) 
        network_test.network_test_guest(machine, domain['name'], 'guest network test')

    network_test.network_test_dom0(machine, 'dom0 network test')

    def report(txt,f):
        if(f):
            print 'INFO: '+txt+' PASS'
        else:
            print 'INFO: ERROR '+txt+' was reset'    # Generate exception 
 
    if (wall.rstrip('\n') != 'images/wallpaper/s6.png'): report('Wallpapwer',0)
    else : report('Wallpaper',1)
    if (vcpu.rstrip('\n') != '2'): report('vcpu',0)
    else : report('vcpu',1)
    if (slot.rstrip('\n') != '7'): report('slot',0)
    else : report('slot',1)
    if (memo.rstrip('\n') != '1048'): report('VM memory range',0)
    else : report('memory',1)
          
    #TODO - Add some basic power operations on host and VM.

def installGuest(machine,vms,steps,build,test_path,caller):
    install_guest(machine, vms)    

def installTools(machine,vms,steps,build,test_path,caller):
    install_tools(machine, vms)

def hostHibernate(machine,vms,steps,build,test_path,caller):
    log(1,'Host Hibernate')
    if caller == 'PVM': tslib.hdx_switch(machine, 1, vms)
    if caller == 'SVM': tslib.hdx_switch(machine, 0, vms)
    if caller == 'noVM': tslib.forcepowerstate(machine, 'off', vms)
    else : tslib.forcepowerstate(machine, 'on', vms)
    sleep(5)
    power_control.xenmgr_hibernate(machine)
    sleep(30)
    power_control.set_s0(machine)
    wait_to_come_up(machine)
    if caller != 'noVM': windows_transitions.wait_for_vms(machine,vms)
    log(2)

def hostSleep(machine,vms,steps,build,test_path,caller):
    log(1,'Host Sleep')
    if caller == 'PVM': tslib.hdx_switch(machine, 1, vms)
    if caller == 'SVM': tslib.hdx_switch(machine, 0, vms)
    if caller == 'noVM': tslib.forcepowerstate(machine, 'off', vms)
    else: tslib.forcepowerstate(machine, 'on', vms)
    sleep(5)
    power_control.xenmgr_sleep(machine)
    sleep(30)
    power_control.set_s0(machine)
    wait_to_come_up(machine, timeout=15)
    if caller != 'noVM': windows_transitions.wait_for_vms(machine,vms,timeout=15)
    log(2)

def hostReboot(machine,vms,steps,build,test_path,caller):
    log(1,'Host Reboot')
    tslib.forcepowerstate(machine, 'on', vms)
    power_control.reboot(machine)
    windows_transitions.vm_poweron(machine)
    log(2)

def hostShutdown(machine,vms,steps,build,test_path,caller):
    log(1,'Host Shutdown')
    tslib.forcepowerstate(machine, 'on', vms)
    power_control.xenmgr_shutdown(machine)
    sleep(30)
    power_control.set_s0(machine)
    wait_to_come_up(machine, timeout=15)
    windows_transitions.vm_poweron(machine)
    log(2)

def xx(machine,vms,steps,build,test_path,caller):                     # Place holder for unimplemented test cases 
    print "Test case is not ready"

def test(machine,vms,steps,build,test_path,caller):                   # For testing
    print "testing..."

def forceShutPVM(machine,vms,steps,build,test_path,caller):
    log(1,'Force Shutdown of PVM')
    tslib.forcepowerstate(machine, 'on', vms)
    tslib.hdx_switch(machine, 1, vms)
    windows_transitions.vm_poweroff(machine, vms) 
    sleep(10)
    windows_transitions.vm_poweron(machine, vms)
    log(2)

def forceShutSVM(machine,vms,steps,build,test_path,caller):
    log(1,'Force Shutdown of SVM')
    tslib.forcepowerstate(machine, 'on', vms)
    tslib.hdx_switch(machine, 0, vms)
    windows_transitions.vm_poweroff(machine, vms)
    sleep(10)
    windows_transitions.vm_poweron(machine, vms)
    log(2)

def shutdownPVM(machine,vms,steps,build,test_path,caller):
    log(1,'Shutdown of PVM')
    tslib.forcepowerstate(machine, 'on', vms)
    tslib.hdx_switch(machine, 1, vms)
    windows_transitions.vm_shutdown_dom0(machine, vms)
    sleep(10)
    windows_transitions.vm_poweron(machine, vms)
    log(2)

def shutdownSVM(machine,vms,steps,build,test_path,caller):
    log(1,'Shutdown of SVM')
    tslib.hdx_switch(machine, 0, vms)
    tslib.forcepowerstate(machine, 'on', vms)
    windows_transitions.vm_shutdown_dom0(machine, vms)
    sleep(10)
    windows_transitions.vm_poweron(machine, vms)
    log(2)

def hibernatePVM(machine,vms,steps,build,test_path,caller):
    log(1,'Hibernate of PVM')
    tslib.forcepowerstate(machine, 'on', vms)
    tslib.hdx_switch(machine, 1, vms)
    windows_transitions.vm_hibernate_dom0(machine, vms)
    sleep(10)
    windows_transitions.vm_poweron(machine, vms)
    windows_transitions.wait_for_vms(machine,vms)
    log(2)

def hibernateSVM(machine,vms,steps,build,test_path,caller):
    log(1,'Hibernate of SVM')
    tslib.hdx_switch(machine, 0, vms)
    tslib.forcepowerstate(machine, 'on', vms)
    windows_transitions.vm_hibernate_dom0(machine, vms)
    windows_transitions.vm_poweron(machine, vms)
    windows_transitions.wait_for_vms(machine,vms)
    log(2)

def sleepPVM(machine,vms,steps,build,test_path,caller):
    log(1,'PVM sleep')    
    tslib.forcepowerstate(machine, 'on', vms)
    tslib.hdx_switch(machine, 1, vms)
    windows_transitions.vm_sleep_dom0(machine, vms)
    windows_transitions.vm_resume(machine, vms)
    windows_transitions.wait_for_vms(machine,vms)
    log(2)

def sleepSVM(machine,vms,steps,build,test_path,caller):
    log(1,'SVM sleep')     
    tslib.hdx_switch(machine, 0, vms)
    tslib.forcepowerstate(machine, 'on', vms)
    windows_transitions.vm_sleep_dom0(machine, vms)
    windows_transitions.vm_resume(machine, vms)
    windows_transitions.wait_for_vms(machine,vms)
    log(2)

def rebootPVM(machine,vms,steps,build,test_path,caller):
    log(1,'PVM reboot')
    tslib.forcepowerstate(machine, 'on', vms)
    tslib.hdx_switch(machine, 1, vms)
    windows_transitions.vm_reboot_dom0(machine, vms)
    log(2)

def rebootSVM(machine,vms,steps,build,test_path,caller):
    log(1,'SVM reboot')
    tslib.hdx_switch(machine, 0, vms)
    tslib.forcepowerstate(machine, 'on', vms)
    windows_transitions.vm_reboot_dom0(machine, vms)
    log(2)

def enableHDX(machine,vms,steps,build,test_path,caller):
    log(1,'Enabling HDX on the VM')
    tslib.forcepowerstate(machine, 'on', vms)
    tslib.hdx_switch(machine, 1, vms)
    log(2)

def poweroffPVM(machine,vms,steps,build,test_path,caller):
    log(1,'Force Power off PVM')
    tslib.hdx_switch(machine, 1, vms)
    tslib.forcepowerstate(machine, 'on', vms)
    windows_transitions.vm_poweroff(machine, vms)
    windows_transitions.vm_poweron(machine)
    log(2)

def poweroffSVM(machine,vms,steps,build,test_path,caller):
    log(1,'Force Power Off SVM')    
    tslib.hdx_switch(machine, 0, vms)
    tslib.forcepowerstate(machine, 'on', vms)
    windows_transitions.vm_poweroff(machine, vms)
    windows_transitions.vm_poweron(machine)
    log(2)

def deleteVM(machine,vms,steps,build,test_path,caller):
    log(1,'Deleting VM')
    tslib.forcepowerstate(machine, 'off', vms)
    run(['xec-vm', '-n', vms, 'delete'],host=machine)

def entry_fn():
    return 0

def desc():
    return 'Placeholder description'

TEST_CASES = [
    { 'description': 'Dummy', 'trigger':'998',
      'function': test, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-204 - XC installation', 'trigger':'1',
      'function': installBuild, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
#    { 'description': 'XCT-206 - Create VM', 'trigger':'3',
#      'function': test, 'bvt_position': 10.0,                            
#      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
#      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
#      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-207 - Install OS', 'trigger':'2',
      'function': installGuest, 'bvt_position': 10.0,                     
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-209 - Install tools', 'trigger':'3',
      'function': installTools, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-223 - Force Shutdown PVM', 'trigger':'4',
      'function': forceShutPVM, 'bvt_position': 10.0,                           
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-222 - Shutdown PVM', 'trigger':'5',
      'function': shutdownPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-221 - Reboot PVM', 'trigger':'6',
      'function': rebootPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-220 - Hibernate Host', 'trigger':'7',
      'function': hostHibernate, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-219 - Sleep Host', 'trigger':'8',
      'function': hostSleep, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-218 - Hibernate PVM', 'trigger':'9',
      'function': hibernatePVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-217 - Sleep PVM', 'trigger':'10',
      'function': sleepPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-215 - Enable HDX', 'trigger':'11',
      'function': enableHDX, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-214 - Hibernate SVM', 'trigger':'12',
      'function': hibernateSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-213 - Sleep SVM', 'trigger':'13',
      'function': sleepSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-212 - Reboot SVM', 'trigger':'14',
      'function': rebootSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-211 - Shutdown SVM', 'trigger':'15',
      'function': shutdownSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-210 - Force Shutdown SVM', 'trigger':'16',
      'function': poweroffSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-227 - Delete Running VM', 'trigger':'17',
      'function': xx, 'bvt_position': 10.0,                            #nLe
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-228 - Delete VM', 'trigger':'18',
      'function': deleteVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
#    { 'description': 'XCT-1739 - Create VM - Win7x64', 'trigger':'19',
#      'function': xx, 'bvt_position': 10.0,                            
#      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
#      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
#      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1740 - Install OS - Win7x64', 'trigger':'20',
      'function': installGuest, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1741 - Install Tools - Win7x64', 'trigger':'21',
      'function': installTools, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1743 - Shutdown SVM - Win7x64', 'trigger':'23',
      'function': shutdownSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1744 - Reboot SVM - Win7x64', 'trigger':'24',
      'function': rebootSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1745 - Sleep SVM - Win7x64', 'trigger':'25',
      'function': sleepSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1746 - Hibernate SVM - Win7x64', 'trigger':'26',
      'function': hibernateSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1747 - Enable HDX - Win7x64', 'trigger':'27',
      'function': enableHDX, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1749 - Sleep PVM - Win7x64', 'trigger':'28',
      'function': sleepPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1750 - Hibernate PVM - Win7x64', 'trigger':'29',
      'function': hibernatePVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1751 - Sleep Host - Win7x64', 'trigger':'30',
      'function': hostSleep, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-1752 - Hibernate Host - Win7x64', 'trigger':'31',
      'function': hostHibernate, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-1753 - Reboot PVM - Win7x64', 'trigger':'32',
      'function': rebootPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1754 - Shutdown PVM - Win7x64', 'trigger':'33',
      'function': shutdownPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-1755 - Force Shutdown PVM - Win7x64', 'trigger':'34',
      'function': poweroffPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x64'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
#    { 'description': 'XCT-39 - Create VM - Win7x32', 'trigger':'35',
#      'function': xx, 'bvt_position': 10.0,                            
#      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
#      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
#      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-40 - Install OS - Win7x32', 'trigger':'36',
      'function': installGuest, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-41 - Install Tools - Win7x32', 'trigger':'37',
      'function': installTools, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-42 - Force Shutdown SVM - Win7x32', 'trigger':'38',
      'function': poweroffSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-44 - Reboot SVM - Win7x32', 'trigger':'40',
      'function': rebootSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-45 - Sleep SVM - Win7x32', 'trigger':'41',
      'function': sleepSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-46 - Hibernate SVM - Win7x32', 'trigger':'42',
      'function': hibernateSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-47 - Enable HDX - Win7x32', 'trigger':'43',
      'function': enableHDX, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-49 - Sleep PVM - Win7x32', 'trigger':'44',
      'function': sleepPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-50 - Hibernate PVM - Win7x32', 'trigger':'45',
      'function': hibernatePVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-51 - Sleep Host - Win7x32', 'trigger':'46',
      'function': hostSleep, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-52 - Hibernate Host - Win7x32', 'trigger':'47',
      'function': hostHibernate, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-53 - Reboot PVM - Win7x32', 'trigger':'48',
      'function': rebootPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-54 - Shutdown PVM - Win7x32', 'trigger':'49',
      'function': shutdownPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-55 - Force Shutdown PVM - Win7x32', 'trigger':'50',
      'function': poweroffPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'win7x32'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-56 - Delete running VM - Win7x32', 'trigger':'51',
      'function': xx, 'bvt_position': 10.0,                            #nLe
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-57 - Delete VM - Win7x32', 'trigger':'52',
      'function': xx, 'bvt_position': 10.0,                            #nLe
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
#    { 'description': 'XCT-20 - Create VM - Vista', 'trigger':'53',
#      'function': xx, 'bvt_position': 10.0,                            
#      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
#      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
#      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-21 - Install OS - Vista', 'trigger':'54',
      'function': installGuest, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-22 - Install Tools - Vista', 'trigger':'55',
      'function': installTools, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-23 - Force Shutdown SVM - Vista', 'trigger':'56',
      'function': poweroffSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-24 - Shutdown SVM - Vista', 'trigger':'57',
      'function': shutdownSVM, 'bvt_position': 10.0,                         
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-25 - Reboot SVM - Vista', 'trigger':'58',
      'function': rebootSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-26 - Sleep SVM - Vista', 'trigger':'59',
      'function': sleepSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-27 - Hibernate SVM - Vista', 'trigger':'60',
      'function': hibernateSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-28 - Enable HDX - Vista', 'trigger':'61',
      'function': enableHDX, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-30 - Sleep PVM - Vista', 'trigger':'62',
      'function': sleepPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-31 - Hibernate PVM - Vista', 'trigger':'63',
      'function': hibernatePVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-32 - Sleep host - Vista', 'trigger':'64',
      'function': hostSleep, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-33 - Hibernate host - Vista', 'trigger':'65',
      'function': hostHibernate, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-34 - Reboot PVM - Vista', 'trigger':'66',
      'function': rebootPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-35 - Shutdown PVM - Vista', 'trigger':'67',
      'function': shutdownPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-36 - Force shutdown PVM - Vista', 'trigger':'68',
      'function': poweroffPVM, 'bvt_position': 10.0,                           
      'arguments' : [('machine', '$(DUT)'), ('vms', 'vista'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-37 - Delete running VM - Vista', 'trigger':'69',
      'function': xx, 'bvt_position': 10.0,                            #nLe
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-38 - Delete VM - Vista', 'trigger':'70',
      'function': xx, 'bvt_position': 10.0,                            #nLe
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
#    { 'description': 'XCT-1 - Create VM - XP', 'trigger':'71',
#      'function': xx, 'bvt_position': 10.0,                            
#      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
#      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
#      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-2 - Instal OS - XP', 'trigger':'72',
      'function': installGuest, 'bvt_position': 10.0,                           
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3 - Install tools - XP', 'trigger':'73',
      'function': installTools, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-4 - Force shutdown SVM - XP', 'trigger':'74',
      'function': poweroffSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-5 - Shutdown SVM - XP', 'trigger':'75',
      'function': shutdownSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-6 - Reboot SVM - XP', 'trigger':'76',
      'function': rebootSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-7 - Sleep SVM - XP', 'trigger':'77',
      'function': sleepSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-8 - Hibernate SVM - XP', 'trigger':'78',
      'function': hibernateSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-9 - Enable HDX - XP', 'trigger':'79',
      'function': enableHDX, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-11 - Standby PVM - XP', 'trigger':'80',
      'function': sleepPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-12 - Hibernate PVM - XP', 'trigger':'81',
      'function': hibernatePVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-13 - Reboot PVM - XP', 'trigger':'82',
      'function': rebootPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-14 - Hibernate Host - XP', 'trigger':'83',
      'function': hostHibernate, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-15 - Reboot PVM - XP', 'trigger':'84',
      'function': rebootPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-16 - Shutdown PVM - XP', 'trigger':'85',
      'function': shutdownPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-17 - Force Shutdown PVM - XP', 'trigger':'86',
      'function': poweroffPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', 'xp'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-18 - Delete running VM - XP', 'trigger':'87',
      'function': xx, 'bvt_position': 10.0,                            #nLe
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-19 - Delete VM - XP', 'trigger':'88',
      'function': xx, 'bvt_position': 10.0,                            #nLe
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-803 - Host Reboot Multiple VMs', 'trigger':'89',
      'function': hostReboot, 'bvt_position': 10.0,                           
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-802 - Host Shutdown Multiple VMs', 'trigger':'90',
      'function': hostShutdown, 'bvt_position': 10.0,                        
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-799-800 - Host Sleep Multiple VMs', 'trigger':'91',
      'function': hostSleep, 'bvt_position': 10.0,                           
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-797-798 - Host Sleep PVM', 'trigger':'92',
      'function': hostSleep, 'bvt_position': 10.0,                           
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'PVM')]},
    { 'description': 'XCT-795-796 - Host Sleep SVM', 'trigger':'93',
      'function': hostSleep, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-793-794 - Host sleep without VMs', 'trigger':'94',
      'function': hostSleep, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'noVM')]},
    { 'description': 'XCT-791-792 - Host Hibernate Multiple Vms', 'trigger':'95',
      'function': hostHibernate, 'bvt_position': 10.0,                         
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-789-790 - Host Hibernate PVM', 'trigger':'96',
      'function': hostHibernate, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'PVM')]},
    { 'description': 'XCT-787-789 - Host Hibernate SVM', 'trigger':'97',
      'function': hostHibernate, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'SVM')]},
    { 'description': 'XCT-785-786 - Host Hibernate without VMs', 'trigger':'98',
      'function': hostHibernate, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', 'noVM')]},
    { 'description': 'XCT-781-782 - Guest Hibernate PVM', 'trigger':'99',
      'function': hibernatePVM, 'bvt_position': 10.0,                           
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-777-778 - Guest Hibernate SVM', 'trigger':'100',
      'function': hibernateSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-775-776 - Guest Sleep PVM', 'trigger':'101',
      'function': sleepPVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-773-774 - Guest sleep SVM', 'trigger':'102',
      'function': sleepSVM, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'Smoke Test - XC Upgrade', 'trigger':'103',
      'function': upgradeBuild, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
]








