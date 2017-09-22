from src.bvtlib.run import run

class InformationCollectionFailure(Exception):
    """failed to find needed information"""

class BadEnumValue(Exception):
    """Bad input value"""

#returns disks in a list, returns None if empty
def list_disks(host,guest):
    disk_list = run(['xec-vm', '-n', guest, 'list-disks'], host=host, line_split=True)
    if len(disk_list) < 1:
        return None
    if '' in disk_list:
        disk_list.remove('')
    return disk_list


#returns the number of the disk on guest, None if no disks
def parsed_list_disks(host,guest):
    """returns the number of the disk on guest, None if no disks"""
    unparsed = list_disks(host,guest)
    if unparsed == None:
        return None
    parsed = []
    for disk in unparsed:
        partial = disk.split('/')
        parsed.append(partial[-1].strip())
    return parsed

def last_disk(host, guest):
    """gives last disk, if no disks returns None"""
    disk_list = parsed_list_disks(host,guest)
    if disk_list == None:
        return None
    return disk_list[-1]

def is_vhd(host,guest,disknum):
    """see if a disk is a vhd"""
    disk_type = run(['xec-vm', '-n', guest, '--disk' , disknum, 'get', 'phys-type'],host=host).strip()
    if disk_type == 'vhd':
        return True
    return False

def is_vhd_valid(host,guest,disknum):
    """see if a vhd is valid, will return False if in use"""
    if not is_vhd(host,guest,disknum):
        return False
    phy_path = run(['xec-vm', '-n', guest, '--disk', disknum, 'get', 'phys-path'],host=host).strip()

    result = run(['vhd-util', 'check', '-n', phy_path],host=host,ignore_failure=True)
    if result[0].strip() == phy_path + ' is valid':
        return True
    return False

def list_vhd(host, guest):
    """finds all vhd on a guest returns the disk nums that are vhd"""
    disks = parsed_list_disks(host,guest)
    vhd_list = []
    for disknum in disks:
         if is_vhd(host, guest, disknum):
             vhd_list.append(disknum)
    return vhd_list

def add_disk(host, guest):   
    return run(['xec-vm', '-n', guest, 'add-disk'], host=host)

def list_vhd_by_name(host,guest):
    disk_nums = list_vhd(host,guest)
    name_list = []
    for disk in disk_nums:
        path = run(['xec-vm', '-n', guest, '--disk', disk, 'get', 'phys-path'], host=host).strip()
        name_list.append(path.split('/')[-1].strip())
    return name_list

def parsed_add_disk(host, guest):
    """returns the number of the disk instead of disk path"""
    unparsed = add_disk(host,guest)
    parsed = unparsed.split('/')
    return parsed[-1].strip()

def add_vhd(host, name, size = 80000):
    #returns the path to the disk
    run(['vhd-util', 'create', '-n', '/storage/disks/' + name, '-s', str(size)],host=host)
    return '/storage/disks/' + name

def create_snapshot(host,path,vhd_path):
    run(['vhd-util', 'snapshot', '-n', path, '-p', vhd_path],host=host) 

def attach_vhd(host,guest,disknum,path):
    run(['xec-vm', '-n', guest, '--disk', disknum, 'attach-vhd', path],host=host)

def disk_type(host, guest, disknum):
    return run(['xec-vm', '-n', guest, '--disk', disknum, 'get', 'mode'],host=host).strip()

def get_disk_snapshot(host,guest,disknum):
    return run(['xec-vm', '-n', guest, '--disk', disknum, 'get', 'snapshot'],host=host).strip()

def set_disk_devtype(host,guest, disknum, devtype):
    run(['xec-vm', '-n', guest, '--disk', disknum, 'set', 'devtype', devtype], host=host)

def set_disk_mode(host, guest, disknum, mode):
    run(['xec-vm', '-n', guest, '--disk', disknum, 'set', 'mode', mode], host=host)

def get_disk_phys_path(host,guest, disknum):
    return (['xec-vm','-n' , guest, '--disk', 'get' ,'phys-path']).strip()

def set_disk_phys_path(host, guest, disknum, path):
    run(['xec-vm', '-n', guest, '--disk', disknum, 'set', 'phys-path', path], host=host)

def set_disk_phys_type(host, guest, disknum, phys_type):
    run(['xec-vm', '-n', guest, '--disk', disknum, 'set', 'phys-type', phys_type], host=host)

def set_disk_snapshot(host, guest, disknum, snapshot):
    #should be none or temporary
    if  snapshot != 'none' and snapshot != 'temporary':
        raise BadEnumValue() 
    run(['xec-vm', '-n', guest, '--disk', disknum, 'set', 'snapshot', snapshot],host=host)

def delete_disk(host,guest, disknum):
    run(['xec-vm', '-n', guest, 'shutdown'], host=host)
    run(['xec-vm', '-n', guest, '--disk', disknum, 'delete'], host=host)

def guest_iso_list(host):
    """lists isos in /storage/isos assumes no random files make their way in here"""
    unparsed = run(['ls', '/storage/isos'],host=host, word_split=True)
    iso_list = []
    for iso in unparsed:
        if iso != '':
            iso_list.append(iso.strip())
    return iso_list

def guest_iso_volume_id_list(host):
    """gets the volume id of the iso, how vm shows the iso"""
    guest_iso_list = guest_iso_list(host)
    volume_list = []
    correct_line = None
    for iso in guest_iso_list:
        unparsed = run(['isoinfo', '-d', '-i', '/storage/isos/' + iso],host=host,line_split=True)
        for line in unparsed:
            if 'Volume' in line and 'id' in line:
                correct_line = line.strip()
                break
        if correct_line == None:
            raise InformationCollectionFailure()
        parse_two = correct_line.split(" ")
        volume_id = parse_two[-1].strip()
        volume_list.append(correct_line.split(" ")[-1].strip())
    return volume_list
        
def iso_volume_id(host, iso):
    """returns volume_id, which is name of it in VM"""
    unparsed = run(['isoinfo', '-d', '-i', '/storage/isos/' + iso],host=host,line_split=True)
    for line in unparsed:
        if 'Volume' in line and 'id' in line:
            parse_one = line.strip()
            break
    parse_two = parse_one.split(" ")
    volume_id = parse_two[-1].strip()
    if volume_id == 'OpenXT-tools':
        volume_id = 'OpenXT-tool'
    return volume_id

def guest_iso_0(host,guest):
    """gets what iso is held in the 0 disk slot of a VM"""
    unparsed = run(['xec-vm', '-n', guest, '--disk', '0', 'get', 'phys-path'],host=host).strip().split('/')
    #parsed = unparsed.split('/')
    iso_0 = unparsed[-1]
    return iso_0.strip()

def set_iso_0(host,guest,iso):
    """sets what iso is held in the 0 disk slot of a VM"""
    run(['xec-vm', '-n', guest, '--disk', '0', 'set', 'phys-path', '/storage/isos/'+iso],host=host)

