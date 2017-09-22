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

"""Run iperf on dom0 and guests"""
from src.bvtlib.exceptions import ExternalFailure
from src.bvtlib.retry import retry
from src.bvtlib.domains import list_vms
from src.bvtlib.run import isfile, run
from src.bvtlib.call_exec_daemon import call_exec_daemon, run_via_exec_daemon
from src.bvtlib.wait_for_windows import wait_for_windows
from src.bvtlib.settings import IPERF_LINUX32_DOWNLOAD, IPERF_LINUX64_DOWNLOAD
from src.bvtlib.settings import IPERF_WINDOWS_DOWNLOAD
from socket import gethostname, gethostbyname
from multiprocessing import Process
from zipfile import ZipFile
# unfotunately the name open in tarfile clashes with builtins so import
# whole module
import tarfile
from hashlib import sha1
from src.bvtlib.temporary_web_server import TemporaryWebServer
from tempfile import mkdtemp

class NoIperfBinaryForUnameOutput(ExternalFailure):
    """Logic to select iperf version did not recognise version"""

class PoorNetworkPerformance(ExternalFailure):
    """Network performance was unacceptable"""

class DidNotFindExpectedIperfBinary(Exception):
    """Did not find expected iperf binary"""

class IperfTransferError(ExternalFailure):
    """Failed to get iperf on to target machine"""

def get_linux_iperf(host=None):
    """Get iperf binary on to host and return its path on that host"""
    iperf = '/tmp/iperf'
    arch = run(['uname', '-a'], host=host)
    print 'INFO: got uname -a output', arch
    if 'i686' in arch:
        download = IPERF_LINUX32_DOWNLOAD
    elif 'x86_64' in arch:
        download = IPERF_LINUX64_DOWNLOAD
    else:
        raise NoIperfBinaryForUnameOutput(arch)
    if isfile(iperf, host=host):
        print 'INFO: already had iperf for', host
    else:
        if not isfile(iperf, host=host):
            run(['wget', '--no-check-certificate', '-O', iperf, download[0]], host=host)
    sha256sum =run(['sha256sum', iperf], word_split=True, host=host)[0]
    if download[1] != sha256sum:
        raise DidNotFindExpectedIperfBinary('want', download,
                                            'have', sha256sum)
    run(['chmod', '+x', iperf], host=host)
    return iperf

def get_windows_iperf(host, destd='C:/iperf'):
    """Put iperf on host at destd"""
    iperf_local = '/tmp/iperf_win.zip'
    if not isfile(iperf_local):
        run(['wget', '--no-check-certificate', '-O', iperf_local,
             IPERF_WINDOWS_DOWNLOAD[0]])
    sha256sum = run(['sha256sum', iperf_local], word_split=True)[0]
    if sha256sum != IPERF_WINDOWS_DOWNLOAD[1]:
        raise DidNotFindExpectedIperfBinary('have', sha256sum,
                                            'want', IPERF_WINDOWS_DOWNLOAD)
    with ZipFile(iperf_local) as zipobj:
        tempd = mkdtemp(suffix='.iperf.tar')
        with tarfile.open(name=tempd+'/iperf.tar', mode='w') as tarobj:
            for zipinfo in zipobj.infolist():
                print 'TRANSFER: transferring %s (%dKB)' % (
                    zipinfo.filename, zipinfo.file_size/1024)
                tarinfo = tarfile.TarInfo(zipinfo.filename)
                tarinfo.size = zipinfo.file_size
                tarobj.addfile(tarinfo, zipobj.open(zipinfo.filename))
        with TemporaryWebServer(tempd) as web:
            call_exec_daemon('unpackTarball', [web.url + '/iperf.tar',
                                               'C:/iperf'], host=host)
        for zipinfo in zipobj.infolist():
            destf = destd+'/'+zipinfo.filename
            if zipinfo.file_size == 0:
                continue
            print 'TRANSFER: checking', destf, zipinfo.file_size
            have = call_exec_daemon('sha1Sum', [destf], host=host)
            want = sha1(zipobj.open(zipinfo.filename).read()).hexdigest()
            if have != want:
                raise IperfTransferError(destf, 'have', have, 'want', want)
            print 'TRANSFER: Correctly transferred', destf, 'hash', have
    return destd+'/iperf.exe'


class IperfServer:
    """Run an iperf server in a separate process"""
    def __init__(self, host, iperf_path):
        self.host = host
        self.iperf_path = iperf_path
    def __enter__(self):
        self.process = Process(target=self.run)
        self.process.start()
        print 'INFO: launched iperf server'
    def __exit__(self, *_):
        self.process.terminate()
        self.process.join()
    def run(self):
        """In the subprocess actually launch iperf"""
        run([self.iperf_path, '-s'], host=self.host)

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
    iperf_client = get_windows_iperf(host) if windows else get_linux_iperf(host)
    with IperfServer(None, get_linux_iperf(None)):
        args = [iperf_client, '-c', gethostbyname(gethostname()), '-t', str(duration)]
        out = (run_via_exec_daemon if windows else run)(args, host=host)
        print 'INFO: iperf reports', out

def network_test_dom0(dut, description, duration=1):
    """Run iperf from dom0"""
    return network_test(dut, description, duration)

def network_test_guest( dut, guest, description, duration=1):
    """Run iperf from windows guest"""
    address = wait_for_windows(dut, guest)
    return network_test(address, description, duration, windows=True)


def entry_fn(dut, guest):
    if guest == ['dom0']:
        network_test_dom0(dut, 'dom0')
    else:
        network_test_guest(dut, guest, guest)
    

def desc():
   return 'Test dom0 networking or test networking in guest VM' 
