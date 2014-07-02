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

"""Run netperf on dom0 and guests"""
from bvtlib.exceptions import ExternalFailure
from bvtlib.retry import retry
from bvtlib.domains import list_vms
from bvtlib.run import isfile, specify, SubprocessError
from bvtlib.call_exec_daemon import call_exec_daemon, run_via_exec_daemon
from bvtlib.wait_for_windows import wait_for_windows
from bvtlib.settings import NETPERF_LINUX_DISTRIBUTION_URL, \
    NETPERF_WINDOWS_DISTRIBUTION_URL
from socket import gethostname

class PoorNetworkPerformance(ExternalFailure): 
    """Network performance was unacceptable"""

class CouldNotUnpackNetperf(Exception):
    """Failed to unpack and install netperf binaries"""

def network_test(host, description, duration=1, windows=False):
    """Test networking performance"""
    print 'INFO: doing network test to', description, 'at', host
    if description == 'all':
        network_test(host, 'dom0', duration=duration)
        for domain in list_vms(host):
            if domain['name'] == 'uivm':
                continue
            print 'check', domain
            vm_address = wait_for_windows(host, domain['name'], timeout=1200)
            
            network_test(vm_address, domain['name'], windows=True)
        return
    if windows:
        if call_exec_daemon('fileExists', ['C:/netperf/netclient.exe'], 
                            host=host):
            print 'INFO: already had netperf on', description
        else:
            print 'INFO: installing netperf for', description
            try:
                call_exec_daemon('unpackTarball', 
                                 [NETPERF_WINDOWS_DISTRIBUTION_URL, 'C:\\'],
                                 host=host)
            except Exception, exc:
                raise CouldNotUnpackNetperf(host, exc)
        netperf = 'C:/netperf/netclient.exe'
    else:
        netperf = '/tmp/usr/local/bin/netperf' 
        go = specify(host=host, cwd='/')
        if (isfile(netperf, host=host)):
            print 'INFO: already had netperf for', description
        else:
            filename = '/tmp/netperf.linux.tar.gz'
            if not isfile(filename, host=host):
                go(['wget', '-O', filename, NETPERF_LINUX_DISTRIBUTION_URL])
                go(['gunzip', '-f', filename])
            go(['tar', 'xvf', filename.replace('.gz', '')], cwd='/tmp')
            if not isfile(netperf, host=host):
                raise CouldNotUnpackNetperf(host, netperf)
    for test in ['TCP_STREAM -- -m 65536 -s 65536 -S 65536 -r 65536 -M 65536', 
                 'TCP_RR', 'TCP_CRR',
                 #'UDP_STREAM', 'UDP_RR'
                 ]:
        tdes = test.split()[0]
        print 'INFO: testing', test, 'traffic in', description
        command = [netperf, '-l', str(duration), '-H',  
                   gethostname(), '-t'] + test.split()
        if windows:
            callback = lambda: run_via_exec_daemon(command, host=host)
        else:
            callback = lambda: go(command)
        out = retry(callback, description='run netperf', timeout=600.0, 
                    catch=[SubprocessError])
        spl = out.split()
        if 'STREAM' in test:
            result = eval(spl[-1])
            good = lambda x: x > 10
            units = 'megabits/second'
        else:
            result = 0.5e6 / eval(spl[-3])
            good = lambda x: x < (500000 if 'CRR' not in test else 500000)
            units = 'microseconds'
        print 'INFO: netperf', tdes, 'result', result, units, \
            'from', description
        if not good(result):
            raise PoorNetworkPerformance(description, tdes, result, units)

def network_test_dom0(dut, description, duration=1):
    """Run netperf from dom0"""
    return network_test(dut, description, duration)

def network_test_guest( dut, guest, description, duration=1):
    """Run netperf from windows guest"""
    address = wait_for_windows(dut, guest)
    return network_test(address, description, duration, windows=True)

TEST_CASES = [
    { 'description': 'Test dom0 networking', 'trigger':'platform ready',
      'function': network_test_dom0, 'bvt':True,
      'options_predicate': lambda options: options.network_test,
      'arguments' : [('dut', '$(DUT)'), ('description', 'dom0') ]},
    { 'description': 'Test networking in $(OS_NAME)', 'trigger':'VM ready',
      'function': network_test_guest, 'bvt':True,
      'options_predicate': lambda options: options.network_test,
      'arguments' : [('dut', '$(DUT)'), ('guest', '$(GUEST)'), 
                     ('description', '$(OS_NAME)')]},
]
