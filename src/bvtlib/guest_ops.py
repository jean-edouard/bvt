#!/usr/bin/python

from src.bvtlib.disk_ops import create_snapshot, is_vhd_valid
from src.bvtlib.guest_info import is_acpi_state, get_system_type, set_system_type, get_largest_domid
from src.bvtlib.run import run
from src.bvtlib.wait_for_guest import wait_for_guest
from src.bvtlib.call_exec_daemon import run_via_exec_daemon, call_exec_daemon
from src.bvtlib.domains import domain_address
from src.bvtlib.settings import VALID_OS_TYPES
import re

class InvalidBootOrder(Exception):
    """Invalid Boot symbol"""

class UnExpectedOs(Exception):
    """Not a valid os for the operation"""

class InformationCollectionFailure(Exception):
    """Unable to collect required information"""

class UnableToSetOSType(Exception):
    """Unable to confirm OS is set to expected type"""

class UnableToDetermineOSFromVHD(Exception):
    """Unable to deteremine OS from VHD from valid OS types"""

def parse_leases():
    out = []
    for spl in run(['cat', '/var/lib/dhcp/dhcpd.leases'], split=True):
        if len(spl) == 0:
            continue
        if spl[0] == 'lease':
            ipaddress = spl[1]
            start = name = None
        if spl[0] == 'starts':
            start = ' '.join(spl[2 : 4])[:-1]
        if spl[0] == 'client-hostname':
            name = spl[-1][1:-2]
        if spl[0] == 'hardware':
            mac = spl[2][:-1]
            if spl == ['}']:
                out.append( (mac.upper(), ipaddress, start, name))
    return out

def get_vm_ip(host, name):
    leases = parse_leases()
    #nic 0 seems like a cop out
    mac = run(['xec-vm', '-n', name, '--nic', '0', 'mac-actual'], host=host, word_split=True)[0]
    for entry in leases:
        if mac == entry[0]:
            return entry[1]
    return None

def get_architecture(host,guest):
   if not is_acpi_state(host,guest,0):
       guest_start(host,guest)
       guest_switch(host,guest)
       wait_for_guest(host,guest)
   os = get_system_type(host,guest)

   if os == 'windows':
       unparsed = run_via_exec_daemon(['systeminfo'], host=domain_address(host,guest),line_split=True)
       for line in unparsed:
           if "System Type" in line:
               correct_line = line.split(" ")
               break
       if correct_line == None:
           print "ERR: Architecture not returned"
           raise InformationCollectionFailure()
       temp = correct_line
       correct_line = None
       for seg in temp:
           if any(char.isdigit() for char in seg):
               correct_line = seg
               break
       if correct_line == None:
           print "ERR: Architecture not returned"
           raise InformaitonCollectionFailure()
       Arch = re.sub("\D", "", correct_line)
       return Arch.strip()

   elif os == 'linux':
       return run(['uname','-m'],host=domain_address(host,guest),ignore_failure=True)[0].strip() 
   else:
       raise UnexpectedOs() 

def create_guest(host, name, desc, memory='6144', vcpus='2', encrypt=False, os='linux', 
                    vhd=None, iso=None):
    #Default-ish options
    dbus_p = run(['xec', 'create-vm'], host=host, word_split=True)[0]
    vm_op = lambda x: run(['xec', '-o', dbus_p, '-i', 'com.citrix.xenclient.xenmgr.vm']+ x,
                    host=host, word_split=True)
    vm_op(['set', 'name', name])
    vm_op(['set', 'memory', memory])
    vm_op(['set', 'wired-network', 'brbridged'])
    vm_op(['set', 'vcpus', vcpus])
    vm_op(['set', 'description', desc])
    vm_op(['set', 'stubdom', 'true'])
    vm_op(['set', 'os', os])
    
    #No need to support wireless nic quite yet
    vm_op(['add-nic'])
   
    #Dependent options
    if os == 'linux':        
        vm_op(['set', 'xci-cpuid-signature', 'true'])
        vm_op(['set', 'viridian', 'false'])
    if iso:
        vm_op(['set', 'cd', iso])
    if vhd:
        #Consider grabbing disk num here as well
        run(['xec-vm', '-n', name, 'add-disk'], host=host)
        run(['xec-vm', '-n', name, '-k', '1', 'set', 'phys-path', vhd], host=host)
    else:
        v_path = run(['xec', 'create-vhd', '80000'], host=host, split=True)[0][0]
        assert v_path.endswith('.vhd')
        ddp = run(['xec-vm', '-n', name, 'add-disk'], host=host, split=True)[0][0]
        dn = ddp.split('/')[-1]
        run(['xec-vm', '-n', name, '-k', dn, 'attach_vhd', v_path], host=host)
    if encrypt:
        key_dir = run(['xec', 'get', 'platform-crypto-key-dirs'],
                      host=host, line_split=True)[0]
        run(['mkdir', '-p', key_dir], host=host)
        phys_path = run(['xec-vm', '-n', name, '--disk', '1',
                        'get', 'phys-path'], host=host, line_split=True)[0]
        assert basename(phys_path).endswith('.vhd')
        vm_vhd_uuid = basename(phys_path)[:-4]
        key_file = (key_dir + '/'+vm_vhd_uuid+',aes-xts-plain,'+
                    '512.key')
        run(['dd', 'if=/dev/urandom', 'of='+key_file,
             'count='+512/8, 'bs=1'],
            host=host)
        run(['vhd-util', 'key', '-n', phys_path, '-k', key_file, '-s'],
            host=host)
    return name

def create_vm_from_template(host,template):
    #create vm using template
    path = run(['xec', 'create-vm-with-template', '/usr/share/xenmgr-1.0/templates/default/' + template],host=host).strip()
    parsed = path.split('/')
    uuid = parsed[-1]
    return uuid.replace('_','-')


def create_vm_and_snapshot(host, name, desc, base_vhd_path, snapshot_name, memory='6144', vcpus='2', encrypt=False, os='windows'):
    snapshot_path = '/storage/disks/' + snapshot_name
    create_snapshot(host,snapshot_path,base_vhd_path)
    create_guest(host, name, desc, memory, vcpus, encrypt, os, vhd=snapshot_path)
    return name

def vm_clean_up_deletion(host,guest):
    """quickly and almost guarentee vm will get deleted"""
    guest_destroy(host,guest)
    guest_delete(host,guest)
 
def get_largest_domid_with_guest(host):
    """creates a temp guest to get the current largest used domid"""
    guest = create_guest(host, "largest_domid_guest", "guest to check largest domid", memory='2048')
    guest_start(host,guest)
    max_domid = get_largest_domid(host)
    vm_clean_up_deletion(host,guest)
    return max_domid

#Default to blocking on these operations, but support the ability
#to not block.
def guest_start(host, name, wait=True):
    run(['xec-vm', '-n', name, 'start'], host=host, wait=wait)

def guest_shutdown(host, name, wait=True):
    run(['xec-vm', '-n', name, 'shutdown'], host=host, wait=wait,timeout = 150.0)

def guest_destroy(host, name, wait=True):
    run(['xec-vm', '-n', name, 'destroy'], host=host, wait=wait)

#Default to using name, but support using uuid instead
def guest_delete(host, name):
    if guest_state(host, name) == 'stopped':
        run(['xec-vm', '-n', name, 'delete'], host=host)
    else:
        print "ERR: GUEST " + str(name) + " not deleted"

def guest_reboot(host,name):
    run(['xec-vm', '-n', name, 'reboot'],host=host)

def guest_switch(host,name):
    run(['xec-vm','-n', name, 'switch'],host=host)

def guest_pause(host, name):
    run(['xec-vm', '-n', name, 'pause'], host=host)

def set_boot_order(host,name,order):
    #would check exclusive, but makes an easy check
    valid_boot = ['c','d','n']
    for letter in order:
        if letter not in valid_boot:
            raise InvalidBootOption()
    run(['xec-vm', '-n', name, 'set', 'boot', order], host=host)

def set_memory(host,name, memory):
    run(['xec-vm', '-n', name, 'set', 'memory', memory], host=host)

def set_vcpu(host,name, vcpu):
    run(['xec-vm', '-n', name, 'set', 'vcpus', vcpu], host=host)

def set_stubdom(host,name,stubdom):
    run(['xec-vm', '-n', name, 'set', 'stubdom', stubdom],host=host)

#below this line might want to move to guest_info

def guest_uuid(host, name, clean=False):
    try:
        out = run(['xec-vm', '-n', name, 'get', 'uuid'], host=host, line_split=True)[0]
        if clean == True:
            return out.replace('-','_',4)
        else:
            return out
    except Exception:
        return None
    
    
def guest_exists(host, name, clean=True):
    uuid = guest_uuid(host, name, clean=clean)
    if uuid is None:
        return False
    out = run(['xec', 'list-vms'], host=host, line_split=True)
    for vm in out:
        if uuid in vm:
            return True
    return False

def guest_state(host, name):
    return run(['xec-vm', '-n', name, 'get', 'state'], host=host, line_split=True)[0]
        
def guest_domid(host, name):
    return int(run(['xec-vm', '-n', name, 'get', 'domid'], host=host).strip())

def guest_type(host, name):
    return run(['xec-vm', '-n', name, 'get', 'type'], host=host).strip()

#copied over to get info, delete once all references to it are moved over
def guest_acpi_state(host, name):
    return run(['xec-vm', '-n', name, 'get', 'acpi-state'], host=host)

def get_os_from_vhd(host,vhd_path):
    """given a local vhd path, determine if its running windows or linux"""
    #loop through given os types in global VALID_OS_TYPES setting and see if we can get it to respond properly
    guest_is = None
    guest_name = create_vm_and_snapshot(host=host, name='get_os_from_vhd_test',desc="get_os_from_vhd_test_desc", base_vhd_path=vhd_path,snapshot_name='get_os.vhd', memory='2048', vcpus='2', encrypt=False, os=VALID_OS_TYPES[0])
    is_vhd_valid(host,guest_name,"1")
    #for os in (os for os in VALID_OS_TYPES if guest_is == None):
    for os in VALID_OS_TYPES:
        print "DEBUG: testing os: \"%s\"" % os
        curr_system_type = None
        set_system_type(host,guest_name,os)
        curr_system_type = get_system_type(host,guest_name)
        if os != curr_system_type:
            raise UnableToSetOSType("unable to confirm os_type \"%s\" is the same as type to test: \"%s\"" % (curr_system_type, os)) 
        guest_start(host,guest_name)
        try:
            wait_for_guest(host,guest_name,timeout=120)
        except:
            print "DEBUG: VM: \"%s\" did not respond as a %s guest" % (guest_name,os)
        else:
            print "DEBUG: assigning current OS to system as determined to be it: \"%s\"" % (os)
            guest_is = os
            break

    vm_clean_up_deletion(host,guest_name)
    print "guest is: \"%s\"" % guest_is
    if guest_is in VALID_OS_TYPES:
        print "DEBUG: given vhd was of OS type: %s" % guest_is 
        return guest_is 
    else:
        print "ERROR: could not determine OS from vhd: %s" % (vhd_path)
        raise UnableToDetermineOSFromVHD("unable to deteremine OS from VHD from valid OS types")


def guest_disk_count(host,guest):
    """function to get the count of 'disks' the guest sees"""
    total_disk_count = 0
    os = get_system_type(host,guest)
    if os == 'windows':
        unparsed = run_via_exec_daemon(['echo', 'list', 'disk', '|', 'diskpart','|','find','"Disk"','|','find','"Online"'],host=domain_address(host, guest, timeout=5),line_split=True)
        #necessary as windows sometimes puts random blank lines at the end
        print "DEBUG: "+',,'.join(unparsed)
        for entry in unparsed:
            if "Disk" in entry:
                total_disk_count += 1
    elif os == 'linux':
        unparsed = run(['lsblk','-l','-o','NAME,TYPE'], host=domain_address(host, guest, timeout=5), timeout=20, check_host_key=False, line_split=True)
        for entry in unparsed:
            if "disk" in entry:
                total_disk_count += 1
    else:
        raise UnexpectedOs() 

    print "DEBUG: returning guest: \"%s\" has %d disks" % (guest,total_disk_count)
    return total_disk_count

def disable_start_on_boot(host,guest):
    """function to set the start-on-boot attribute per guest to false"""
    run(['xec-vm', '-n', guest, 'set', 'start-on-boot', 'false'], host=host)

def enable_start_on_boot(host,guest):
    """function to set the start-on-boot attribute per guest to true"""
    run(['xec-vm', '-n', guest, 'set', 'start-on-boot', 'true'], host=host)
    
def get_start_on_boot(host,guest):
    """function to get the start-on-boot attribute per guest"""
    return run(['xec-vm', '-n', guest, 'get', 'start-on-boot'], host=host)

def get_username(host,guest,addr,os):
    if os == 'windows':
        return run_via_exec_daemon(['whoami'], host=addr).split('\\')[1].strip('\n')
