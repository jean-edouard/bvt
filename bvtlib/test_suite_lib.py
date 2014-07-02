#! /usr/local/bin/python2.6
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

from bvtlib import exceptions,sleep,pxe_install_xc,Session,reboot_test
from bvtlib import install_tools,network_test,connection,connect_to_exec_daemon
from bvtlib import test_failure, soak, domains, accelerate_graphics, installer_test
from bvtlib import store_status_report, fork, get_build, sysmark_test, retry
from bvtlib import set_pxe_build, validate_dut_name, install_synchronizer, install_guest, start_vm
import sys, optparse, time, os, twisted.web.util, pwd
from bvtlib import install_guest,database_cursor
import os

class CannotConnect(exceptions.ExternalFailure): pass


def check_vm_status( machine):
        can_connect = []
        f=1
        with (connection.connect(host=machine,
                       user='root')) as sh_dut:
            domlist = domains.list_vms(sh_dut)
            for domain in domlist:
                if (domain['name']!='uivm'): 
                    try:
                        proxy=(connect_to_exec_daemon.
                        connect_to_exec_daemon(
                              session, domain['uuid'], timeout=10))
                    except Exception, e:
                        print 'POWER:', 'trying to connect to exec daemon',e 
                        f=0
            if(f): return
            else: raise CannotConnect("failed: vm/s not reacheable")


def try_to_connect( machine):
        can_connect= []
        try:
            with connection.connect(host=machine,user='root')as sh_dut:
                print 'POWER:', 'connect to',machine 
        except Exception, e:
            print 'POWER:', 'got exception trying to connect', e 
        else:
            can_connect.append(sh_dut)
        if can_connect != []: return (sh_dut) 
        raise CannotConnect("failed: host is not reacheable")

def runlog(txt):
        print time.asctime( time.localtime(time.time()) ),": ",txt


def get_hdx_state( machine, vm):
            with (connection.connect(host=machine,
                       user='root')) as sh_dut: 
                go = lambda x: sh_dut.verified_launch(x,timeout=120).addCallback(lambda y: y[0])
                r = go('xec-vm -n '+vm+' get type') 
                return (r)


def get_vm_powerstate( machine, vm):
            with (connection.connect(host=machine,
                       user='root')) as sh_dut:
                go = lambda x: sh_dut.verified_launch(x,timeout=120).addCallback(lambda y: y[0])
                r = go('xec-vm -n '+vm+' get state')
                return (r)
 

def hdx_switch( machine, onoff, vm_name):
            with (connection.connect(host=machine,
                       user='root')) as sh_dut:
                 hdx_state = get_hdx_state( machine, vm_name)
                 hdx_state = hdx_state.rstrip('\n') 
                 if(onoff):
                     if(hdx_state=='svm'):
                        go = lambda x: sh_dut.verified_launch(x,timeout=120).addCallback(lambda y: y[0])
                        sleep.sleep(20)
                        runlog('Shutting down '+vm_name+' and enabling HDX mode')
                        soak.soak_down(machine,'vm_shutdown',vm_name)
                        sleep.sleep(10)
                        go('xec-vm -n '+vm_name+' set type pvm')
                        sleep.sleep(10)
                        runlog('Powering on '+vm_name+' PVM')
                        soak.soak_down(machine,'vm_poweron',vm_name)
                        sleep.sleep(120)
                        runlog('Rebooting after driver update')
                        soak.soak_down(machine,'vm_reboot',vm_name)
                        runlog(vm_name+' PVM is ready')
                     elif(hdx_state=='pvm'):
                        runlog(vm_name+' is PVM')   
                 else:
                     if(hdx_state=='svm'):
                        runlog(vm_name+' is SVM')
                     elif(hdx_state=='pvm'):
                        go = lambda x: sh_dut.verified_launch(x,timeout=120).addCallback(lambda y: y[0])
                        sleep.sleep(20)
                        runlog('Shutting down '+vm_name+' to disable HDX')
                        soak.soak_down(machine,'vm_shutdown',vm_name)
                        sleep.sleep(10)
                        go('xec-vm -n '+vm_name+' set type svm')
                        sleep.sleep(10)
                        runlog('Powering on '+vm_name+' SVM')
                        soak.soak_down(machine,'vm_poweron',vm_name)
                        runlog(vm_name+' SVM is ready')


def forcepowerstate( machine, reqstate, vm_name):
                 with connection.connect(host=machine,user='root') as sh_dut:
                     domlist = domains.list_vms(sh_dut)
#                 sh_dut = retry.retry(lambda: try_to_connect( machine),
#                    'retrying connection to dom0',pace=10,timeout=5,
#                        catch=[Exception])
                 for domain in domlist:
                     if(vm_name == 'all' or vm_name == domain['name']):
                         pow_state = get_vm_powerstate( machine, domain['name'])
                         pow_state = pow_state.rstrip('\n')
                         if(reqstate == 'on'):
                             if(pow_state!='running'):
                                go = lambda x: sh_dut.verified_launch(x,timeout=120).addCallback(lambda y: y[0])
                                runlog('Powering on '+domain['name']+' VM')
                                soak.soak_down(machine,'vm_poweron',domain['name'])
                                runlog(domain['name']+' VM is ready')
                         elif(reqstate == 'off'):
                             if(pow_state=='running'):
                                go = lambda x: sh_dut.verified_launch(x,timeout=120).addCallback(lambda y: y[0])
                                runlog('Shutting down VM')
                                soak.soak_down(machine,'vm_shutdown',domain['name'])
                                runlog(domain['name']+' VM is shutdown')


def odtd_install_guest( dut, guest='st_xp', kind='iso'):
    print time.asctime( time.localtime(time.time()) ),':  HEADLINE: installing',guest,'on',dut,'from',kind
    assert kind in ['iso','vhd']
    with connection.connect(host=dut,user='root') as sh_dut:
        # wget fails if target exists, so make sure it doesn't
        url = 'http://www.cam.xci-test.com/xc_dist/auto_install/sans_tools/st_'+guest+'.'+kind
        sdir = '/storage/'+('isos' if kind == 'iso' else 'disks')
        sh_dut.verified_launch('mkdir -p '+sdir)
        dest_file = (sdir+'/st_'+guest+'.'+kind)
        if not sh_dut.isfile(dest_file):
            install_guest.download_image(sh_dut, kind, guest, dest_file)
        rubyd = ('{"name"=>"%s", '
                 '"image_path"=>"images\\/vms/000_XenClient_h32bit_256.png", '
                 '"config.memory"=>"1024", "cd"=>"st_%s.iso", '
                 '"description"=>"%s", '
                 '"config.vcpus"=>"1", '
                 '"wired_network"=>"bridged"}' % (guest,guest,guest))
        vmid_raw,_ = sh_dut.verified_launch("xec create '"+rubyd+"'")
        full_vmid = vmid_raw.split()[0]
        short_vmid = full_vmid.split('/')[-1].replace('_','-')
        vhdid_raw, _ = sh_dut.verified_launch(
            'xec -o '+full_vmid+
            ' -i com.citrix.xenclient.xenmgr.vm addEmptyDisk 40')
        vhdid = vhdid_raw.split()[0]
        sh_dut.verified_launch('xec -o '+full_vmid+' -i '+
                                     'com.citrix.xenclient.xenmgr.vm setDisk '+
                                     vhdid+' device hda')
        vhd_raw, _ = sh_dut.verified_launch(
            'db-read /vm/'+short_vmid+'/config/disk/'+vhdid+'/path')
        vhd_spl = vhd_raw.split()
        vhd_path = vhd_spl[0] if vhd_spl else vhd_raw
        assert vhd_path.endswith('.vhd')
        if kind == 'vhd':
            sh_dut.verified_launch('mv '+dest_file+' '+vhd_path)
        start_vm.start_vm(sh_dut, guest)
        connect_to_exec_daemon.connect_to_exec_daemon( short_vmid)
        return (vhd_path)




