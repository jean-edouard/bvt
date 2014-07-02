#
# Copyright (c) 2012 Citrix Systems, Inc.
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
from bvtlib.exceptions import ExternalFailure
from bvtlib.retry import retry
from bvtlib.domains import list_vms, domain_address
from bvtlib.run import isfile, specify, SubprocessError
from bvtlib.call_exec_daemon import call_exec_daemon, run_via_exec_daemon
from bvtlib.wait_for_windows import wait_for_windows
from bvtlib.wait_to_come_up import wait_to_come_up, wait_to_go_down
from bvtlib.windows_transitions import wait_for_windows_to_come_up, wait_for_windows_to_go_down
from bvtlib.pxe_install_xc import pxe_install_xc
from bvtlib.install_guest import install_guest
from bvtlib.install_tools import install_tools
from bvtlib.tslib import find_guest_vms
from bvtlib.run import run
from bvtlib import power_control, tslib, network_test, windows_transitions
from bvtlib import testModules
from socket import gethostname
from time import sleep
import string
import random
import os

def installBuild(machine,vms,steps,build,test_path,caller):
    pxe_install_xc(machine, build) 

def installGuest(machine,vms,steps,build,test_path,caller):
    install_guest(machine, vms, encrypt_vhd=True)

def installTools(machine,vms,steps,build,test_path,caller):
    install_tools(machine, vms)

def xx(machine,vms,steps,build,test_path,caller):                     # Place holder for unimplemented test cases 
    print "Test case is not ready"

def test(machine,vms,steps,build,test_path,caller):                   # For testing
    print "Testing..."

def tpmstatus(machine):
    r = run(['cryptsetup','luksDump','/dev/xenclient/config'], host=machine)
    if 'Key Slot 0: ENABLED' in r:
        return 0
    else: return 1

def stubdomStatusDom(machine,vm):    # checks if subdom is running in dom0
    domid = run(['xec-vm','-n',vm,'get','domid'], host=machine)
    print 'INFO: domid of ',vm,' is ',domid
    r = run(['ps','-ef'], host=machine)
    r = string.split(r,'\n')
    l = []
    for line in r:
         if 'qemu' in line: l.append(line)
    tslib.cmdResponse('\n'.join(l), 'ps aux | grep qemu')
    searchStr = ('-d '+domid).rstrip('\n')
    if searchStr in ' '.join(l): return 1
    else: return 0

def xenopsliststatus(machine,vm,count):
    r = run(['xenops','list'], host=machine)
    tslib.cmdResponse(r, 'xenops list')
    c = len(string.split(r,'\n'))
    if c>count:       
        print "INFO: New entry found in xenops list. Seems like stubdom service VM started with VM boot"
        print "INFO: NOTE - BVT does not know if a stubdom listed in xenops-list is associated to the VM under test"
        return 1 
    elif c<count:
        print "INFO: From xenops list result it seems like like stubdom service VM stopped for the VM under test"
        print "INFO: NOTE - BVT does not know if a stubdom listed in xenops-list is associated to the VM under test"
        return 0 
    else: tslib.pauseToDebug("Entries in xenops list unchanged")

def checkStubdom(machine,vm,count,expected):  
    if expected == stubdomStatusDom(machine,vm) and expected != xenopsliststatus(machine,vm,count): return 1
    else: return 0

def xenopslistcount(machine,vm):  
    tslib.forcepowerstate(machine, 'on', vm)
    r = run(['xenops','list'], host=machine)
    tslib.cmdResponse(r, 'xenops list')
    return len(string.split(r,'\n'))

def tpmsetup(machine,vms,steps,build,test_path,caller):
    r = run(['tpm-setup'], host=machine)
    tslib.cmdResponse(r, 'tpm-setup')
    if 'TPM setup successful -- please reboot!' not in r or 'fail' in r:
        tslib.pauseToDebug("TPM setup - FAILED") 
    else:
        power_control.platform_transition(machine, 'reboot')
        wait_to_go_down(machine)
        tslib.interact(machine, "At the TPM protection screen, enter password and choose to reseal the device")
        wait_to_come_up(machine) 

def checkTPM(machine,vms,steps,build,test_path,caller):
    r = run(['cryptsetup','luksDump','/dev/xenclient/config'], host=machine)
    tslib.cmdResponse(r, 'cryptsetup luksDump /dev/xenclient/config')
    f=0
    for i in [1,7]:
        if 'Key Slot '+str(i)+': ENABLED' not in r: f=1
    for i in [0,2,3,4,5,6]:
        if 'Key Slot '+str(i)+': DISABLED' not in r: f=1
    if f: tslib.pauseToDebug("Command response is not as expected")
     
    r = run(['cat','$(find','/sys/','-name','pcrs)'], host=machine)     
    tslib.cmdResponse(r, 'cat $(find /sys/ -name pcrs)')

def editfs(machine,vms,steps,build,test_path,caller):
    r = run(['mount','-o','rw,remount','/'], host=machine)
    tslib.cmdResponse(r, 'cryptsetup luksDump /dev/xenclient/config')
    r = run(['touch','/testfolder1'], host=machine)
    tslib.cmdResponse(r, 'cryptsetup luksDump /dev/xenclient/config')

    power_control.platform_transition(machine, 'reboot')
    wait_to_go_down(machine)
    tslib.interact(machine, "At the TPM protection screen, choose shutdown. Ensure that machine shutsdown")

    power_control.set_s0(machine)
    tslib.interact(machine, "At the TPM protection screen, choose continue. Enter the wrong password 3 times. Ensure that machine shutsdown")

    power_control.set_s0(machine)
    tslib.interact(machine, "At the TPM protection screen, choose continue. Enter the correct password. Choose not to reseal the device")
    wait_to_come_up(machine)

    power_control.platform_transition(machine, 'reboot')
    wait_to_go_down(machine)
    tslib.interact(machine, "Ensure that TPM protection screen is shown, enter password and choose to reseal the device")
    wait_to_come_up(machine)

    print "Rebooting the device to check if reseal has taken effect. TPM screen should not be seen anymore"
    power_control.platform_transition(machine, 'reboot')
    wait_to_go_down(machine)
    wait_to_come_up(machine)

def hdxPowerops(machine,vms,steps,build,test_path,caller):
    stubdom=stubdomStatusDom(machine,vms)
    count = xenopslistcount(machine,vms)
    if 'vm_force_shutdown' not in steps:
        testModules.forceShutPVM(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'vm_hibernate' not in steps:
        testModules.hibernatePVM(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'vm_shutdown' not in steps:
        testModules.shutdownPVM(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'vm_sleep' not in steps:
        testModules.sleepPVM(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'vm_reboot' not in steps:
        testModules.rebootPVM(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'host_hibernate' not in steps:
        testModules.hostHibernate(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'host_sleep' not in steps:
        testModules.hostSleep(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'host_reboot' not in steps:
        testModules.hostReboot(machine,vms,steps,build,test_path,caller) 
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'host_shutdown' not in steps:
        testModules.hostShutdown(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
     
def nonhdxPowerops(machine,vms,steps,build,test_path,caller):
    stubdom=stubdomStatusDom(machine,vms)
    if 'vm_force_shutdown' not in steps:
        testModules.forceShutSVM(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'vm_hibernate' not in steps:
        testModules.hibernateSVM(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'vm_shutdown' not in steps:
        testModules.shutdownSVM(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'vm_sleep' not in steps:
        testModules.sleepSVM(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'vm_reboot' not in steps:
        testModules.rebootSVM(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'host_hibernate' not in steps:
        testModules.hostHibernate(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'host_sleep' not in steps:
        testModules.hostSleep(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'host_reboot' not in steps:
        testModules.hostReboot(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 
    if 'host_shutdown' not in steps:
        testModules.hostShutdown(machine,vms,steps,build,test_path,caller)
        if not checkStubdom(machine,vms,count,stubdom): tslib.pauseToDebug("Stubdom malfunction after power operation") 

def enableSELINUX(machine,vms,steps,build,test_path,caller):
    r = run(['getenforce'], host=machine)
    tslib.cmdResponse(r, 'getenforce')
    if 'Enforcing' in r: tslib.pauseToDebug("SELINUX is already enabled. Restart the test with correct settings")
    r = run(['mount','-o','rw,remount','/'], host=machine)
    r = run(['echo','"newrole','-r','sysadm_r"','>','/root/permission.ny'], host=machine)
    r = run(['echo','"mount','-o','rw,remount','/"','>','/root/run.ny'], host=machine)    
    r = run(['echo','"getenforce"','>>','/root/run.ny'], host=machine)
    r = run(['echo','"sed','-i','"s/SELINUX=.*/SELINUX=permissive/"','/etc/selinux/config"','>','/root/disable_selinux.ny'], host=machine)
    r = run(['chmod','777','/root/*.ny'], host=machine)
    r = run(['sed','-i','"s/SELINUX=.*/SELINUX=enforcing/"','/etc/selinux/config'], host=machine)
    tslib.cmdResponse(r, 'sed -i "s/SELINUX=.*/SELINUX=enforcing/" /etc/selinux/config')
    power_control.platform_transition(machine, 'reboot')
    tslib.interact(machine, "Wait XC to bootup. Run /root/permission.ny & run.ny from dom0. Verify that selinux policy is returned as Enforcing")

def disableSELINUX(machine,vms,steps,build,test_path,caller):
    tslib.interact(machine, "Run /root/permission.ny,run.ny & disable_selinux.ny from dom0. Reboot the host and wait to come up.")
    r = run(['getenforce'], host=machine)
    tslib.cmdResponse(r, 'getenforce')
    if 'Permissive' not in r: tslib.pauseToDebug("Command response is not as expected")

def enableStartOnBoot(machine,vms,steps,build,test_path,caller):
    print "INFO: Enabling autoboot for ",vms," VM"
    r = run(['xec-vm','-n',vms,'set','start-on-boot','true'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set start-on-boot true')
    print "INFO: Rebooting host"
    power_control.reboot(machine)
    r = wait_for_windows(machine, vms, timeout=300)
    print 'INFO:',vms,' powered on with XC bootup'

def disableStartOnBoot(machine,vms,steps,build,test_path,caller):
    print "INFO: Disabling autoboot for ",vms," VM"
    r = run(['xec-vm','-n',vms,'set','start-on-boot','false'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set start-on-boot false')
    print "INFO: Rebooting host"
    power_control.reboot(machine)
    r = run(['xec-vm','-n',vms,'get','state'], host=machine)
    if 'stopped' not in r: tslib.pauseToDebug("VM started with XC boot and this is not expected")
    else: print 'INFO:',vms,'did not start on XC boot'

def policyAudio(machine,vms,steps,build,test_path,caller):
    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['xec-vm','-n',vms,'set','policy-audio-access','false'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set policy-audio-access false')
    windows_transitions.vm_poweron(machine, vms)
    tslib.interact(machine, "Play audio on the test VM and ensure that it fails") 

    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['xec-vm','-n',vms,'set','policy-audio-access','true'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set policy-audio-access true')
    windows_transitions.vm_poweron(machine, vms)
    tslib.interact(machine, "Play audio on the test VM and ensure that audio plays")

def getDeviceID(machine,vms,steps,build,test_path,caller):
    r = run(['lspci','-nn'], host=machine)
    r = string.split(r,'\n')
    l = [] 
    for i in r: 
        if '[0c03]' in i: l.append(i) 
    tslib.cmdResponse('\n'.join(l), 'lspci -nn | grep \'\[0c03\]\'')
    r = '\n'.join(l)
    l1=r.split()   
    c=0
    num=[]
    id=[]
    for i in l1:
        if '8086' in i: num.append(c) 
        if len(num)>=2: break 
        c=c+1
    l2=l1[num[0]].split(':')
    l3=l2[0].split('[')
    l4=l2[1].split(']')
    id.append('0x'+l3[1]) 
    id.append('0x'+l4[0])

    l2=l1[num[1]].split(':')
    l3=l2[0].split('[')
    l4=l2[1].split(']')
    id.append('0x'+l3[1])
    id.append('0x'+l4[0])
    return id

def enableusbPassthrough(machine,vms,steps,build,test_path,caller):
    (vendor_id1,device_id1,vendor_id2,device_id2) = getDeviceID(machine,vms,steps,build,test_path,caller)
    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['xec-vm','-n',vms,'add-pt-rule','0x0c03',vendor_id1,device_id1], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n vms add-pt-rule 0x0c03'+vendor_id1+' '+device_id1)
    r = run(['xec-vm','-n',vms,'add-pt-rule','0x0c03',vendor_id2,device_id2], host=machine)    
    tslib.cmdResponse(r, 'xec-vm -n vms add-pt-rule 0x0c03'+vendor_id2+' '+device_id2)
    windows_transitions.vm_poweron(machine, vms)
    tslib.interact(machine, "Perform VM reboot if required. Plugin a usb device and verify if the device is passed through to the VM")

def disableusbPassthrough(machine,vms,steps,build,test_path,caller):
    (vendor_id1,device_id1,vendor_id2,device_id2) = getDeviceID(machine,vms,steps,build,test_path,caller)
    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['xec-vm','-n',vms,'delete-pt-rule','0x0c03',vendor_id1,device_id1], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n vms delete-pt-rule 0x0c03'+vendor_id1+' '+device_id1)
    r = run(['xec-vm','-n',vms,'delete-pt-rule','0x0c03',vendor_id2,device_id2], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n vms delete-pt-rule 0x0c03'+vendor_id2+' '+device_id2)
    windows_transitions.vm_poweron(machine, vms)
    tslib.interact(machine, "Plugin a usb device and verify that it is not passed through to the VM")

def audioPassthrough(machine,vms,steps,build,test_path,caller):
    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['xec-vm','-n',vms,'add-pt-rule','0x0403','any','any'], host=machine)
    tslib.cmdResponse(r,'xec-vm -n <vmname> add-pt-rule 0x0403 any any')
    windows_transitions.vm_poweron(machine, vms)
    r = run(['xec-vm','-n',vms,'list-pt-pci-devices'], host=machine)
    tslib.cmdResponse(r,'xec-vm -n '+vms+' list-pt-pci-devices')
    tslib.interact(machine, "Verify if the o/p of list-pt-pci-devices is as expected")
    tslib.interact(machine, "Verify from the VM that a new audio device is detected. Install driver and proceed")

def policyTests(machine,vms,steps,build,test_path,caller):    #TODO USB policy to be added
    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['xec-vm','-n',vms,'set','policy-cd-access','false'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set policy-cd-access false')
    r = run(['xec-vm','-n',vms,'set','policy-print-screen','false'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set policy-print-screen false')
    windows_transitions.vm_poweron(machine, vms)
    tslib.interact(machine, "Verify that CD cannot be accessed from the VM")
    tslib.interact(machine, "Verify that print screen is disabled")

    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['xec-vm','-n',vms,'set','policy-cd-access','true'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set policy-cd-access true')
    r = run(['xec-vm','-n',vms,'set','policy-cd-recording','false'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set policy-cd-recording false')
    r = run(['xec-vm','-n',vms,'set','policy-modify-vm-settings','false'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set policy-modify-vm-settings false')
    windows_transitions.vm_poweron(machine, vms)
    tslib.interact(machine, "Verify that CD is accessible but cannot be burned from the VM")
    tslib.interact(machine, "Verify that VM settings cannot be modified")

    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['xec-vm','-n',vms,'set','policy-modify-vm-settings','true'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set policy-modify-vm-settings true')
    r = run(['xec-vm','-n',vms,'set','policy-cd-recording','true'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set policy-cd-recording true')
    r = run(['xec-vm','-n',vms,'set','policy-print-screen','true'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n '+vms+' set policy-print-screen true')
    windows_transitions.vm_poweron(machine, vms)
    tslib.interact(machine, "Verify that CD can be accessed and burned from the VM")
    tslib.interact(machine, "Verify that VM settings can be modified")
    tslib.interact(machine, "Verify that print screen is enabled for the VM")

def nilfvm(machine,vms,steps,build,test_path,caller):
    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['cd','/storage/nilfvm','nilfvm-create','--rootfs=nilfvm-rootfs.i686.cpio.bz2','--size=256','--config=service-nilfvm'], host=machine)
    tslib.cmdResponse(r, 'nilfvm-create --rootfs=nilfvm-rootfs.i686.cpio.bz2 --size=256 --config=service-nilfvm')
    vm_uuid = run(['xec-vm','-n',vms,'get','uuid'], host=machine)
    vm_uuid = vm_uuid.rstrip('\n')
    tslib.cmdResponse(vm_uuid, 'xec-vm -n '+vms+' get uuid')
    r = run(['xec-vm','-u',vm_uuid,'set','track-dependencies','true'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -u '+vm_uuid+' set track-dependencies true')
    nilfvm_uuid = run(['xec-vm','-n',nilfvm01,'get','uuid'], host=machine)
    r = run(['xec-vm','-u',vm_uuid,'--nic','0','set','backend-uuid',nilfvm_uuid], host=machine)
    tslib.cmdResponse(r, 'xec-vm -u '+vm_uuid+' --nic 0 set backend-uuid '+nilfvm_uuid)

def secondnilfvm(machine,vms,steps,build,test_path,caller):    
    print "Not implemented"

def enableStubdom(machine,vms,steps,build,test_path,caller):
    status = run(['xec-vm','-n',vms,'get','stubdom'], host=machine)
    if 'true' in status: 
        print "INFO: stubdom is already enabled, exiting.." 
        exit()
    count = xenopslistcount(machine,vms) 
    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['xec-vm','-n',vms,'set','stubdom','true'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n'+vms+'set stubdom true')
    windows_transitions.vm_poweron(machine, vms)
    if not checkStubdom(machine,vms,count,0): tslib.pauseToDebug("qemu is either running in dom0 or service VM have not started")  

def disableStubdom(machine,vms,steps,build,test_path,caller):
    status = run(['xec-vm','-n',vms,'get','stubdom'], host=machine)
    if 'false' in status:
         print "INFO: stubdom is already disabled, exiting.."
         exit()
    count = xenopslistcount(machine,vms)
    tslib.forcepowerstate(machine, 'off', vms)
    r = run(['xec-vm','-n',vms,'set','stubdom','false'], host=machine)
    tslib.cmdResponse(r, 'xec-vm -n'+vms+'set stubdom false')
    windows_transitions.vm_poweron(machine, vms)
    if not checkStubdom(machine,vms,count,1): tslib.pauseToDebug("qemu is either not running in dom0 or service VM have not stopped")

def enableSnapshot(machine,vms,steps,build,test_path,caller):
    dummy = str(random.randint(10000,20000))
    vm_address = domain_address(machine, vms)
    r = run(['xec-vm','-n',vms,'--disk','1','get','snapshot'], host=machine)
    if 'none' in r:
        tslib.forcepowerstate(machine, 'off', vms)
        r = run(['xec-vm','-n',vms,'--disk','1','set','snapshot','temporary'], host=machine)
        tslib.cmdResponse(r, 'xec-vm -n '+vms+' --disk 1 set snapshot temporary')
        snapshot = run(['xec-vm','-n',vms,'--disk','1','get','snapshot'], host=machine)
        tslib.cmdResponse(r, 'xec-vm -n '+vms+' --disk 1 get snapshot')
        if 'temporary' not in snapshot: tslib.pauseToDebug("xec failed to enable snapshot")
        windows_transitions.vm_poweron(machine, vms)
        windows_transitions.vm_reboot_dom0(machine, vms)
    res = run_via_exec_daemon(['mkdir','C:\\Users\\Administrator\\Desktop\\'+dummy],host=vm_address, wait=True)
    windows_transitions.vm_reboot_dom0(machine, vms)
    res = run_via_exec_daemon(['dir','C:\\Users\\Administrator\\Desktop\\'],host=vm_address, wait=True) 
    if dummy in res: tslib.pauseToDebug("Snapshot enabled: Old folders found after reboot") 
  
def disableSnapshot(machine,vms,steps,build,test_path,caller):
    dummy = str(random.randint(10000,20000))
    vm_address = str(domain_address(machine, vms))
    r = run(['xec-vm','-n',vms,'--disk','1','get','snapshot'], host=machine)
    if 'temporary' in r:
        tslib.forcepowerstate(machine, 'off', vms)
        r = run(['xec-vm','-n',vms,'--disk','1','set','snapshot','none'], host=machine)
        tslib.cmdResponse(r, 'xec-vm -n '+vms+' --disk 1 set snapshot none')
        snapshot = run(['xec-vm','-n',vms,'--disk','1','get','snapshot'], host=machine)
        tslib.cmdResponse(r, 'xec-vm -n '+vms+' --disk 1 get snapshot')
        if 'none' not in snapshot: tslib.pauseToDebug("xec failed to disable snapshot")
        windows_transitions.vm_poweron(machine, vms)
        for i in range(2): windows_transitions.vm_reboot_dom0(machine, vms) 
    res = run_via_exec_daemon(['mkdir','C:\\Users\\Administrator\\Desktop\\'+dummy],host=vm_address, wait=True)
    windows_transitions.vm_reboot_dom0(machine, vms)
    res = run_via_exec_daemon(['dir','C:\\Users\\Administrator\\Desktop\\'],host=vm_address, wait=True)       
    if dummy not in res: tslib.pauseToDebug("Snapshot disabled: Old folders lost after reboot")         

TEST_CASES = [
    { 'description': 'Dummy', 'trigger':'999',
      'function': test, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-2449 - Installing a VM with encrypted VHD', 'trigger':'104',
      'function': installGuest, 'bvt_position': 10.0,                            
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-2450 - Install XenClient Tools', 'trigger':'105',
      'function': installTools, 'bvt_position': 10.0,                   
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3883 - Run tpm-setup', 'trigger':'106',
      'function': tpmsetup, 'bvt_position': 10.0,                   
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3884 - Checking for the completion of tpm-setup', 'trigger':'107',
      'function': checkTPM, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3885 - Make the file system rewritable', 'trigger':'108',
      'function': editfs, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3886 - Power Ops when TXT is enabled with no 3D graphics VMs', 'trigger':'109',
      'function': nonhdxPowerops, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': ' XCT-3887 - Power Ops when TXT is enabled with 3D graphics enabled VMs are poweredon', 'trigger':'110',
      'function': hdxPowerops, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3888 - Upgrading with TXT enabled', 'trigger':'111',
      'function': xx, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3889 - Enable enforcement of SE Linux and XSM policy for dom0', 'trigger':'112',
      'function': enableSELINUX, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3890 - Disabling SELinux Enforcement', 'trigger':'113',
      'function': disableSELINUX, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-2451 - Configure HDX VM with Nvidia/ATI GPU', 'trigger':'114',
      'function': xx, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3891 - Enable Autoboot to 3D graphics enabled VM', 'trigger':'115',
      'function': enableStartOnBoot, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3891 - Disable Autoboot to 3D graphics enabled VM', 'trigger':'202',
      'function': disableStartOnBoot, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': ' XCT-3892 - Seamless Mouse Switching', 'trigger':'116',
      'function': xx, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3896 - Enable audio device assignment to one VM', 'trigger':'117',
      'function': audioPassthrough, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-2453 - Remove audio emulation from VM', 'trigger':'118',
      'function': policyAudio, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-2471 - Enable USB Controller Pass-through to a guest when TXT is enabled', 'trigger':'119',
      'function': enableusbPassthrough, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-2471 - Disable USB Controller Pass-through to a guest when TXT is enabled', 'trigger':'203',
      'function': disableusbPassthrough, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3897-3898-3899-3900-3901-3902 - Policies', 'trigger':'120',
      'function': policyTests, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3903 - Changing Seamless Application Sharing Border Colour', 'trigger':'121',
      'function': xx, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3904 - Reset on Boot', 'trigger':'122',
      'function': enableSnapshot, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3904 - Reset on Boot', 'trigger':'201',
      'function': disableSnapshot, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3905 - Enable Control domain network access', 'trigger':'123',
      'function': xx, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3906 - Disable Control domain network access', 'trigger':'124',
      'function': xx, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3907 - Attaching a User VM to nilfvm', 'trigger':'125',
      'function': nilfvm, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3909 - nilfvm - PowerOps', 'trigger':'126',
      'function': xx, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3908 - Creating Second nilfvm', 'trigger':'127',
      'function': secondnilfvm, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3910 - nilfvm - AutoBoot', 'trigger':'128',
      'function': xx, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3911 - viptables add/modify/edit from dom0', 'trigger':'129',
      'function': xx, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-3912 - viptables add/modify/edit from any other domain', 'trigger':'130',
      'function': xx, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-4093 - Attach a stubdom', 'trigger':'131',
      'function': enableStubdom, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
    { 'description': 'XCT-4094 - Detach stubdom', 'trigger':'132',
      'function': disableStubdom, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),      
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},

    { 'description': 'template', 'trigger':'200',      
      'function': test, 'bvt_position': 10.0,
      'arguments' : [('machine', '$(DUT)'), ('vms', '$(VMLIST)'),
      ('steps', '$(TESTSTEPS)'), ('build', '$(BUILD)'),
      ('test_path', '$(TESTPATH)'), ('caller', '$(CALLER)')]},
]








