#! /usr/local/bin/python2.6
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

from src.bvtlib import exceptions
from src.bvtlib.retry import retry
from src.bvtlib.domains import list_vms
from src.bvtlib.run import isfile, specify, SubprocessError
from src.bvtlib.call_exec_daemon import call_exec_daemon, run_via_exec_daemon
from src.bvtlib.wait_for_windows import wait_for_windows
from src.bvtlib.run import run
from src.bvtlib.start_vm import start_vm
from src.bvtlib import power_control
from src.testcases.accelerate_graphics import accelerate_graphics  
from socket import gethostname
from time import sleep
import os

class CannotConnect(exceptions.ExternalFailure): pass

def find_guest_vms(dut):
    domlist = list_vms(dut)
    list = []
    for domain in domlist:
         if domain['name'] not in ['uivm', 'ndvm']: list.append(domain)
    return list

def check_vm_status(machine):
        can_connect = []
        f=1
        domlist = domains.list_vms(machine)
        for domain in domlist:
            if (domain['name']!='uivm'):
                try:
                    call_exec_daemon('dir',host = machine)
                except Exception, e:
                    print 'POWER:', 'trying to connect to exec daemon',e
                    f=0
        if(f): return
        else: raise CannotConnect("failed: vm/s not reacheable")

def try_to_connect(machine):
        can_connect= []
        try:
            go = specify(host=machine, cwd='/')
            go(['uptime'])  
        except Exception, e:
            print 'POWER:', 'got exception trying to connect', e 
        else:
            can_connect.append("err")
        if can_connect != []: return  
        raise CannotConnect("failed: host is not reacheable")

def check_for_no_connection(machine):
        can_connect= []
        try:
            go = specify(host=machine, cwd='/')
            go(['uptime'])
        except Exception, e:
            print 'POWER:', 'got exception trying to connect', e
        else:
            can_connect.append("err")
        if can_connect == []: return
        raise CannotConnect("failed: host did not reboot/shutdown")

def get_vm_powerstate(machine, vm):
        r =  run(['xec-vm', '-n', vm, 'get', 'state'], host=machine)
        return r

def get_hdx_state(machine, vm):
        r = run(['xec-vm', '-n', vm, 'get', 'gpu'], host=machine)
        return r

def forcepowerstate(machine, reqstate, vm_name='all'):
        domlist = find_guest_vms(machine)
        for domain in domlist:
            if(vm_name == 'all' or vm_name == domain['name']):
                pow_state = get_vm_powerstate(machine, domain['name'])
                pow_state = pow_state.rstrip('\n')
                if(reqstate == 'on'):
                    if(pow_state!='running'):
                        start_vm(machine, domain['name']) 
                elif(reqstate == 'off'):
                    if(pow_state=='running'):
                        run(['xec-vm', '-n', domain['name'], 'shutdown'], host=machine)

def hdx_switch(machine, onoff, vm_name):
    hdx_state = get_hdx_state(machine, vm_name)
    hdx_state = hdx_state.rstrip('\n')
    if(onoff):
        if(hdx_state==''):
            forcepowerstate(machine, 'on', vm_name)
            accelerate_graphics(machine, vm_name)
            sleep(60)
            windows_transitions.vm_reboot_dom0(machine, vm_name) 
    else:
        if(hdx_state=='hdx'):
            forcepowerstate(machine, 'off', vm_name)
            run(['xec-vm', '-n', vm_name, 'set', 'gpu', "''"], host=machine)


def odtd_install_guest(dut, guest='st_xp', kind='iso'):
    print 'HEADLINE: installing',guest,'on',dut,'from',kind
    sdir = '/storage/isos' 
    dest_file = (sdir+'/st_'+guest+'.'+kind)
    install_guest.download_image(dut, kind, guest, dest_file)
    rubyd = ('{"name"=>"%s", '
                 '"image_path"=>"images\\/vms/000_XenClient_h32bit_256.png", '
                 '"config.memory"=>"1024", "cd"=>"st_%s.iso", '
                 '"description"=>"%s", '
                 '"config.vcpus"=>"1", '
                 '"wired_network"=>"bridged"}' % (guest,guest,guest))
    vmid_raw = run(['xec', 'create', rubyd], host=dut)
    full_vmid = vmid_raw.split()[0]
    short_vmid = full_vmid.split('/')[-1].replace('_','-')
    vhdid_raw = run(['xec', '-o', full_vmid, '-i', 'com.citrix.xenclient.xenmgr.vm addEmptyDisk', '40'], host=dut)  
    vhdid = vhdid_raw.split()[0]
    run(['xec', '-o', full_vmid, '-i', 'com.citrix.xenclient.xenmgr.vm', 'setDisk', vhdid, 'device', 'hda'], host=dut) 
    run(['db-read /vm/', short_vmid, '/config/disk/', vhdid, '/path'], host=dut) 
    vm_address = start_vm(dut, guest, timeout=start_timeout, busy_stop=busy_stop)
    print 'INSTALL_GUEST: start_vm returned, address', vm_address
    ensure_stable(vm_address, 30, description = guest + ' on '+dut)
    print 'INSTALL_GUEST: VM stable'
    print 'INSTALL_GUEST: dir c: replied with %d bytes' % (
        len(run_via_exec_daemon(['dir', 'C:\\'], host=vm_address)))
    return vm_address

def keyboardRes():
    while 1:
        print "go    ->   To continue"
        print "sr    ->   To collect status report"
        var = raw_input()
        if 'go' in var: return

def interact(dut, txt):
    print "\n<<<<< TODO >>>>> : ",txt
    keyboardRes()

def cmdResponse(res, cmd, head='CMD OUTPUT'):
    print '\n','INFO:','-'*5,head,':',cmd
    print 'INFO: ',res.rstrip('\n')
    print '-'*5,"END",'-'*(len(head)+len(cmd)-5),'\n'

def pauseToDebug(txt):
    print "ERROR: ",txt,".. Collect Status Report if necessary"
    keyboardRes()

def log(type,txt=''):
    if type == 1: print 'INFO: ','-'*10,' STARTING : ',txt,'-'*10
    if type == 2: print 'INFO: ','-'*10,' END ','-'*10

