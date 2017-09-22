#assumes list of cds is decently short as check currently uses N^2 algorthim
#check to make sure passthrough of cds is exclusive
#get_cd_list not guarenteed with multiple cds
#tries to assign all cd's to every VM, and after each assign checks the intergrity



from src.bvtlib.run import run
from src.bvtlib.guest_info import list_vms_uuid
from src.bvtlib.device_ops import get_cd_list, assign_cd
from src.bvtlib.guest_ops import create_vm_and_snapshot, vm_clean_up_deletion
from src.bvtlib.host_ops import get_vhd_from_url
import random
from time import sleep


class MultiCDAssign(Exception):
    """A CD is assigned to mutiple VMs"""

class NotEnoughVMToTest(Exception):
    """Either 1 or 0 VMs so impossible for a cd to be assigned to multiple"""


def rand_assign(host, cd_list, vm_list):
    for cd in cd_list:
        for i in range(0,9):
            vm = (random.choice(vm_list))
            assign_cd(host, '', cd, vm)
            exclusive(host)

def exclusive(host):
   
    lines = run(['db-ls', '/xenmgr/cdassign/'], host=host,line_split=True)
    #lines = block.splitlines()
    #due to how db-ls works first line is unimportant
    del lines[0]
    split = []
    for lastspot, cd in enumerate(lines):
        if cd != '':
        #due to how line_split is
            split.append(cd.split('='))
            #split[*][0] hold cd id
            #split[*][1] hold uuid of vm it is assigned to
            for obj in split:
                if obj[0] == split[lastspot][0]:
                    if obj[1] != split[lastspot][1]:
                        raise MultiCDAssign(split)
    return True

def standard_assign(host, cd_list, vm_list):
    for cd in cd_list:
        for vm in vm_list:
            assign_cd(host, '', cd, vm)
            exclusive(host)

def cd_exclusive_test(host, vhd_url):
    
    try:
        exclusive(host)
        guest = 'exclusive-1'
        guest2 = 'exclusive-2'
        path = get_vhd_from_url(host, vhd_url)

        name1 = create_vm_and_snapshot(host, guest, 'Test vm', path, 'exclusive-cd-snap.vhd')
        name2 = create_vm_and_snapshot(host, guest2, 'Test vm', path, 'exclusive-cd-snap2.vhd')

        cd_list = get_cd_list(host)
        vm_list = list_vms_uuid(host)
        if len(vm_list) <= 1:
            raise NotEnoughVMToTest()

        #try to assign each cd to all vm's, see if it breaks
        standard_assign(host,cd_list,vm_list)
        #just throw around random assigns to see if CD can get assigned to 2.
        rand_assign(host,cd_list,vm_list)

        if exclusive(host):
            print "Mutually exclusive kept, test succeeded"
    except:
        raise

    finally:
        vm_clean_up_deletion(host, guest)
        vm_clean_up_deletion(host, guest2)
    

def entry_fn(dut, url):
    cd_exclusive_test(dut, url) 

def desc():
    return "check to make sure passthrough of cd is exclusively locking, only one VM can have a cd at a time"
