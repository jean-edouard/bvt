#!/usr/bin/python

from optparse import OptionParser
from src.bvtlib.test_nodes import NODES
from src.bvtlib.run import run
from src.bvtlib.test_results import record_result, gen_result_html
from subprocess import Popen, PIPE
import fcntl, time, random, sys, traceback, threading

class SubprocessException(Exception):
    """There was a subprocess error."""

filepts = []

def report(test_id, name, out):
        record_result(test_id, name, 'FAIL')
    
def calculate_flight_number():
    random.seed(time.time())
    return random.randint(0,100000000)

#NOTE: If 1 bvt process takes 2+ nodes, and we spawn subprocs for, make sure we don't exit
# this process or we lose locks on the nodes, can probably just do equivalent of C's join()
# Also, consider recording the Node ID/IP address and record test pass/fails for each node.
#Also we're generating zombie processes when we raise exceptions and pass in threads so need to deal with those
def acquire_nodes(num_nodes):
    if(num_nodes > 10):
        raise NodeAcquireException()
    nodes = []
    for i in range(10):
        if len(nodes) == num_nodes:
            break
        f = open('nodes/node'+str(i), "w")
        filepts.append(f)
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            nodes.append(i)
        except (IOError):
            print 'Node %d locked.' %i
            pass
    if len(nodes) == 0:
        return None
    return nodes

def go(jobs, test_id, node):
    logf = open('/var/www/results/logs/log_'+str(test_id)+'_'+str(node), "w")
    for job in jobs:
        try:
            #run(job[1],timeout=3600, log_file='/var/www/results/logs/log_'+str(test_id))
            process = Popen(job[1], stdout=logf, stderr=logf, stdin=PIPE, shell=False, cwd=None, env={})
            process.wait()
            if(process.returncode != 0):
                raise SubprocessException
            record_result(test_id, job[0], 'PASS', node)
        except Exception as ex:
            record_result(test_id, job[0], 'FAIL', node, reason=sys.exc_info()[0])
            print sys.exc_info()[1]
            print traceback.format_exc()
        print 'Job COMPLETE'
    print 'Jobs Complete'

def autotest():
    thr = []
    test_id = calculate_flight_number() 
    print 'INFO: Flight ID number is: ', test_id
    parser = OptionParser()
    parser.add_option('--nodes', action='store', help='Try to run tests on n nodes.')
    
    options, args = parser.parse_args()
    if options.nodes is not None:
        nodes = acquire_nodes(int(options.nodes))
        if not nodes:
            print 'No available testing nodes.'
            return
        else:
            print nodes

    for i in range(len(nodes)):
        mac, ip = NODES[nodes[i]]

        #Loop over a job iterable and try
        jobs = [ ('INSTALL_XT',['./experiments.py', '-m', ip, '--mac-address', mac, '--build', '/tc/rogersc/build', '-x']),
                 ('PERMISSIONS',['./experiments.py', '-m', ip, '--elevate']),
                 ('CHECK_MOUNTS',['./experiments.py', '-m', ip, '--check-mounts']),
                 ('TEMPLATE_STRESS',['./experiments.py', '-m', ip, '--templateSStress']),
                 ('GET_VHD', ['./experiments.py', '-m', ip, '--getVHD', '--vhd-url', '192.168.1.1/vhds/Debian.vhd', '--vhd-name', 'Debian.vhd']),
                 ('UPDOWN_STRESS',['./experiments.py', '-m', ip, '--upDownStress', '--vhd-name','/storage/disks/Debian.vhd']),
                 ('CHECK_MAC', ['./experiments.py', '-m', ip, '--check-mac-addresses'])
               ]
        thr.append(threading.Thread(target=go,args=(jobs,test_id,nodes[i])))
        #t = threading.Thread(target=go,args=(jobs,test_id,nodes[i]))
        #t.start()
        #t.join()
    for t in thr:
        t.start()
    for t in thr:
        t.join()
        
        #go(jobs, test_id)
    #for t in thr:
    #    t.join()
    gen_result_html(test_id, nodes)     
        
if __name__ == '__main__':
    autotest()
