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

"""Simple serial logging"""
from multiprocessing import Process
from bvtlib.run import run
from time import time
from bvtlib.mongodb import get_autotest, get_logging
from os import kill, getpid
from signal import SIGKILL
from traceback import print_exc
from socket import gethostname
from time import sleep

PID = getpid()
HOSTNAME = gethostname()

def do_syslog_tail(dut):
    """Tail syslog on dut"""
             

def do_logging(dut, result_id):
    """Perform logging"""
    try:
        mdb = get_autotest()
        ldb = get_logging()
        dut_doc = mdb.duts.find_one({'name': dut})

        print 'CONSOLE: preparing console logging for', dut, 'result', result_id
        portstring = dut_doc.get('serial_port')
        if portstring:
            print 'INFO: using sympathy tail for', dut, portstring
            host, port = portstring.split(':')
            logfile = '/root/sympathy/'+port+'.log'
            run(['pkill', '-9', '-f', logfile], host=host, ignore_failure=True)
            command =['tail', '-F', logfile]
            phrase = 'SERIAL'
        else:
            print 'INFO: using /var/log/messages tail for', dut
            command = ['tail', '-c', '0', '--follow=name', 
                       '--retry', '/var/log/messages']
            host = dut
            phrase = 'MESSAGES'

        def got_output(data):
            """Log ouptut"""
            for line in data.split('\n'):
                if 'EIP' in line or 'RIP' in line or 'nobody cares' in line or \
                        'oops' in line.lower() or 'panic' in line.lower():
                    print 'HEADLINE: serial console displayed', line
                if result_id:
                    ts = time()
                    handle = '%s_con_%f_%s_%d' % (dut, ts, HOSTNAME, PID)
                    terms = {'message': line, 'kind':phrase,
                             'time':time(), '_id': handle}
                    ldb.logs.save(terms)
                print phrase+':', line
                if 'avc:  denied' in line:
                    print 'AVC:', line
        while 1:
            print 'CONSOLE: launching console logging system'
            try:
                run(command, host=host,
                    output_callback=got_output,
                    timeout=24*60*60)
            except Exception, exc:
                print 'WARNING: console logging failed; will retry'
            sleep(1)
    except Exception, exc:
        print 'INFO: console logging failed with', exc

class ConsoleMonitor:
    def __init__(self, dut, result_id):
        self.dut = dut
        self.result_id = result_id
    def __enter__(self):
        """Start console loggingg for dut"""
        self.process = Process(target=do_logging, 
                               args=(self.dut,self.result_id))
        self.process.start()
        print 'CONSOLE: launched console logging system for', self.dut
    def __exit__(self, _type, value, traceback):
        out, ec = run (['ps', '--no-headers', '-o', 'pid', '--pid', 
                    str(self.process.pid)], ignore_failure=True)
        for pidt in out.split():
            child = int(pidt)
            kill(child, SIGKILL)
        self.process.terminate()
        self.process.join()
        print 'CONSOLE: stopped console logging system'
