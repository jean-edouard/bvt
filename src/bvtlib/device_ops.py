#Contain operation of devices such as CD-rom
from src.bvtlib.run import run
from src.bvtlib.guest_ops import guest_uuid


def get_cd_list(host):
    #need to test on machine with mutiple cd drives to guarentee format of xec command
    lines = run(['xec', '-o', '/host', 'list-cd-devices'], host=host, line_split=True)
    cd_list=[]
    id_lines=[]
    for i in range(0,len(lines)/7):
        id_lines.append(lines[i*7 + 1].strip())
    for line in id_lines:
        line = line.split('=')
	cd_list.append(line[1][1:])
    return cd_list

def assign_cd(host, guest, device_id, uuid =""):
    if uuid == "":
        uuid = guest_uuid(host, guest)
    run(['xec', '-o', '/host', 'assign-cd-device', device_id, "1", uuid], host=host,line_split=True)
