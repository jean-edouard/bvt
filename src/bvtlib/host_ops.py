#!/usr/bin/python

from src.bvtlib import mongodb
from src.bvtlib.run import run, specify
from src.bvtlib.retry import retry

def get_bus(dut):
    """Query mongo for the bus of secondary nic.  If it isn't there, assume
        nic is on bus 01."""
    mdb = mongodb.get_autotest()
    dut_doc = mdb.duts.find_one({'name': dut})
    if dut_doc.get('nic-bus'):
        return dut_doc['nic-bus']
    else:
        return "01"

def mount_debugfs(host):
    run(['mount', '-t', 'debugfs', 'none', '/sys/kernel/debug'], host=host)

def is_debugfs_mounted(host):
    out = run(['ls', '-A', '/sys/kernel/debug'], host=host).strip()
    if out != "":
        return True
    return False

def get_vhd_from_url(host, url):
    """Return the path to the vhd. If it doesn't exist, bvt will download it from
       the provided url"""
    split = url.split('/')
    name = split[len(split)-1]
    job = specify(host=host)
    _, result = run(['ls', '/storage/disks/'+name], host=host, ignore_failure=True)
    if result > 0:
        retry(lambda: job(['wget', '-q', '-O', '/storage/disks/'+name, url], timeout=3600), timeout=7200, description='download'+url)
    return '/storage/disks/'+name

def host_reboot(host):
    run(['reboot'], host=host)

def does_template_exist(host,template):
    #fn to confirm if template exists in the template directory of the host
    template_list = run(['find','/usr/share/xenmgr-1.0/templates/default','-type','f','-exec', 'basename','{}',';'],host=host,line_split=True)
    for host_template in template_list:
        if template in host_template:
            print "DEBUG: template %s exists on host" % template
            return True
    return False
    
