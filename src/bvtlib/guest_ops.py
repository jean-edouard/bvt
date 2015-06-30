#!/usr/bin/python
from src.bvtlib.run import run


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
                      host=dut, line_split=True)[0]
        run(['mkdir', '-p', key_dir], host=dut)
        phys_path = run(['xec-vm', '-n', name, '--disk', '1',
                        'get', 'phys-path'], host=dut, line_split=True)[0]
        assert basename(phys_path).endswith('.vhd')
        vm_vhd_uuid = basename(phys_path)[:-4]
        key_file = (key_dir + '/'+vm_vhd_uuid+',aes-xts-plain,'+
                    '512.key')
        run(['dd', 'if=/dev/urandom', 'of='+key_file,
             'count='+512/8, 'bs=1'],
            host=dut)
        run(['vhd-util', 'key', '-n', phys_path, '-k', key_file, '-s'],
            host=dut)
    return name

#Default to blocking on these operations, but support the ability
#to not block.
def guest_start(host, name, wait=True):
    run(['xec-vm', '-n', name, 'start'], host=host, wait=wait)

def guest_shutdown(host, name, wait=True):
    run(['xec-vm', '-n', name, 'shutdown'], host=host, wait=wait)

def guest_destroy(host, name, wait=True):
    run(['xec-vm', '-n', name, 'destroy'], host=host, wait=wait)

def guest_delete(host, name):
    if guest_state(host, name) == 'stopped':
        run(['xec-vm', '-n', name, 'delete'], host=host)

def guest_uuid(host, name, clean=False):
    try:
        out = run(['xec-vm', '-n', name, 'get', 'uuid'], host=host, line_split=True)[0]
        if clean == True:
            return out.replace('-','_',4)
        else:
            return out
    except Exception:
        return None
    
    
def guest_exists(host, name):
    uuid = guest_uuid(host, name)
    if uuid is None:
        return False
    out = run(['xec', 'list-vms'], host=host, line_split=True)
    for vm in out:
        if uuid in vm:
            return True
    return False

def guest_state(host, name):
    return run(['xec-vm', '-n', name, 'get', 'state'], host=host, line_split=True)
