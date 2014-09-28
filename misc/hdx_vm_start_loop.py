#! /scratch/autotest_python/bin/python
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

###
# XENCLIENT BASIC TESTS
# Reboot loop of a HDX VM
#
# Author: Andrew Peace

from bvtlib import domains
from bvtlib import sleep, start_vm

import sys
import getopt

SHUTDOWN_TIMEOUT = 120


class VMNotFound(Exception): pass
class VMDidNotShutDown(Exception): pass


def create_vm(sh_dut, name, memsize_mb):
    rubyd = ('{"name"=>"%s", '
             '"image_path"=>"images\\/vms/000_XenClient_h32bit_256.png", '
             '"config.memory"=>"%d", "cd"=>"", '
             '"description"=>"Made by autotest", '
             '"config.vcpus"=>"1", '
             '"wired_network"=>"bridged"}' % (
            name, memsize_mb))
    vmid_raw, _ = sh_dut.verified_launch("xec create '" + rubyd + "'", timeout=20)
    vmid_spl = vmid_raw.split()
    if len(vmid_spl) == 0: raise install_guest.BadXecCreateOutput(vmid_raw)
    full_vmid = vmid_spl[0]
    short_vmid = full_vmid.split('/')[-1].replace('_','-')

    return (short_vmid)


def accelerate_graphics(sh_dut, vmid):
    print 'INFO: setting pv-addons-installed'
    sh_dut.verified_launch('xec-vm -u "' + vmid +
                                '" set pv-addons-installed true')
    print 'INFO: setting',vmid,'to PVM'
    sh_dut.verified_launch('xec-vm -u "' + vmid +
                                 '" set type pvm')
     
def vm_from_vm_list(vm_list, vmid):
    vm_list_f = [v for v in vm_list if v['uuid'] == vmid]
    print vm_list, vm_list_f, vmid
    if len(vm_list_f) == 1:
        return vm_list_f[0]
    elif len(vm_list_f) == 0:
        raise VMNotFound, vmid
    else:
        raise RuntimeError, "Multiple VMs matching uuid %s found" % vmid


USAGE = """Usage: hdx_vm_start_loop,py -m <device to test> [-r] [-v vmid]
              [-i iterations]

  -m should specify a machine in the BVT pool
  -r indicates that a reboot should be requested.  If not specified, we
      expect the VM to reboot itself within 60s of booting.  This may
      be because it has no OS installed, for instance.
  -v specifies a VM to test with.  If none is specified, an empty VM is
      created an dused. 
  -i specifies the number of iterations to perform.  Default is 100.
"""


def main(session):
    USE_VMID = ""
    REQUEST_SHUTDOWN = False
    DUT_NAME = None
    TEST_ITERATIONS = 100
    INIT_RASTER_HACK = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "m:rv:hi:H")
        for opt, val in opts:
            if opt == "-m":
                DUT_NAME = val
            elif opt == "-r":
                REQUEST_SHUTDOWN = True
            elif opt == "-v":
                USE_VMID = val
            elif opt == "-h":
                print USAGE
            elif opt == "-i":
                TEST_ITERATIONS = int(val)
            elif opt == "-H":
                INIT_RASTER_HACK = True

        if not DUT_NAME:
            raise RuntimeError, "Must specify device to test."
    except Exception, e:
        print "Invalid argsuments.  " + str(e)
        print USAGE
        sys.exit(1)

    with connection.connect(host=DUT_NAME, user="root") as sh_dut:
        print "connected"
        if USE_VMID:
            vmid = USE_VMID
        else:
            vmid = create_vm(sh_dut, "testvm", 256)
        accelerate_graphics(sh_dut, vmid)

        for i in range(TEST_ITERATIONS):
            print "******** Starting test iteration %d" % i

            # start the VM:
            start_vm.start_vm(sh_dut, vmid)

            # if required, signal the VM to shutdown:
            if REQUEST_SHUTDOWN:
                proxy = connect_to_exec_daemon.connect_to_exec_daemon(vmid)
                proxy.callRemote("shutdown")

            # wait for VM to be in shut-down state:
            for i in range(60):
                sleep.sleep(1)
                vm_list = domains.list_vms(sh_dut)
                vm = vm_from_vm_list(vm_list, vmid)
                if vm['status'] == 'stopped':
                    break
            else:
                raise VMDidNotShutDown
            sleep.sleep(4)

            if INIT_RASTER_HACK:
                sh_dut.verified_launch("init_raster")
                sh_dut.verified_launch("killall input_server")
                sleep.sleep(4)

if __name__ == "__main__":
    Session.main(main)
