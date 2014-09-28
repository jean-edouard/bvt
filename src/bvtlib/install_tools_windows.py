#
# Copyright (c) 2014 Citrix Systems, Inc.
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

"""Install XenClient tools into Windows VM"""
from src.bvtlib.domains import find_domain
from src.bvtlib.call_exec_daemon import call_exec_daemon, run_via_exec_daemon, Fault
from src.bvtlib.have_driver import have_driver
from src.testcases.archive_vhd import archive_vhd
from src.bvtlib.run import run
from src.bvtlib.wait_for_windows import wait_for_windows, ensure_stable
from src.bvtlib.wait_for_windows import wait_for_guest_to_start, wait_for_guest_to_go_down
from src.bvtlib.start_vm import start_vm_if_not_running
from src.bvtlib.reboot_windows_vm import reboot_windows
from src.bvtlib import autoit_generator
from src.bvtlib.settings import XENSETUP_PATH_PATTERN, \
    TOOLS_LOG_FILE, EXPECTED_MSIS, EXPECTED_SERVICES, \
    UNATTENDED_PATH_PATTERN
from multiprocessing import Process
from time import sleep
from src.bvtlib.time_limit import TimeoutError
from socket import error
from traceback import print_exc
from src.bvtlib.soft_shutdown_guest import soft_shutdown_guest
from src.bvtlib.install_dotnet import install_dotnet
from src.bvtlib.windows_guest import make_tools_iso_available
from src.bvtlib.domains import domain_address
from src.bvtlib.exceptions import UnableToInstallTools, ToolsAlreadyInstalled

class ToolsIsoMissing(Exception):
    """Tools ISO not found in dom0"""

class DevCertFailureException(Exception):
    """Failed to install developer certs for tools."""


def loop_run_program(target_exe, vm_address):
    """Run process in loop"""
    while 1:
        print 'INSTALL_TOOLS: starting', target_exe, 'on', vm_address

        try:
            run_via_exec_daemon([target_exe], host=vm_address,
                                timeout=24*60*60)
        except Exception, exc:
            print 'failed with', exc
        sleep(5)


def start_prompt_remover(vm_address):
    """Start our interactive GUI prompt invoker, and return
    a control tuple suitable for stop_prompt_remover"""
    call_exec_daemon('unpackTarball', [None, 'C:\\'], host = vm_address)
    script = autoit_generator.install_tools_script
    for line in script.split('\n'):
        print 'AUTOIT:', line
    target_exe = autoit_generator.compile(vm_address,
                                          'prompt_remover_generated', script)
    autorun_dir = "C:\\docume~1\\admini~1\\startm~1\\Programs\\Startup"
    run_via_exec_daemon(['mkdir', autorun_dir], host=vm_address,
                        ignore_failure=True)
    autorun_promptremover_file = autorun_dir+'\\promptremove.bat'
    call_exec_daemon('createFile',
                     [autorun_promptremover_file, target_exe+'\r\n'],
                     host=vm_address)

    process = Process(target=loop_run_program, args=(target_exe, vm_address))
    process.start()
    return process, target_exe

def kill_prompt_remover(vm_address):
    """Kill the prompt remover"""
    try:
        run_via_exec_daemon(['taskkill', '/IM',
                             'prompt_remover_generated.exe'],
                            host=vm_address, ignore_failure=True)
    except error, exc:
        print 'INSTALL_TOOLS: ignoring socket error', exc, \
            'killing prompt remover'
    except TimeoutError, exc:
        print 'INSTALL_TOOLS: ignoring timeout error', exc, \
            'killing prompt remover'

def stop_prompt_remover(control, vm_address):
    """Stop our interactive GUI prompt invoker. target_exe is the result
    of calling start_prompt_remover"""
    process, _ = control
    process.terminate()
    kill_prompt_remover(vm_address)

def get_msi_versions(vm_address):
    """Return the MSI version installed (e.g. "6.2.14883") or
    None if no MSI is installed"""
    content = """
import _winreg, sys
versions = {}
for base in [
  "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall",
  "SOFTWARE\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"]:
    try:
       uninstall = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, base)
    except WindowsError:
       continue   
    try:
       i = 0
       while 1:
           sub = _winreg.EnumKey(uninstall, i)
           subk = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, base+'\\'+sub)
           j = 0
           progname = version = None
           try:
               while 1:
                   name, value, _ = _winreg.EnumValue(subk, j)
                   if name == 'DisplayName':
                        progname = value
                   if name == 'DisplayVersion':
                        version = value
                   #print >>sys.stderr, i,j, sub, 'entry', name, value
                   j += 1
           except WindowsError:
               pass
           if progname:
               versions[progname] = version
           i += 1
    except WindowsError:
        pass
print versions
""".replace('\\', '\\\\')
    call_exec_daemon('createFile', ['C:\\list_installed_programs.py', content],
                     host=vm_address)
    try:
        versions = eval(run_via_exec_daemon(['C:\\list_installed_programs.py'],
                                            host=vm_address))
        print 'INSTALL_TOOLS: versions installed=', versions
    finally:
        call_exec_daemon('removeFile', ['C:\\list_installed_programs.py'], host=vm_address)
        pass
    return versions


def get_running_services(vm_address):
    """Return the set of services running on vm_address"""
    services = set([
        ' '.join(line) for line in
        run_via_exec_daemon(['net', 'start'], split=True,
                            host=vm_address)[2:-4]])
    print 'INSTALL_TOOLS: services running', sorted(services)
    return services


    
def tools_install_problems(host, guest):
    """Return a string describing reasons why the tools install is bad or None
    if it is good for VM identified by host, guest pair"""
    bad = []
    vm_address = domain_address(host, guest, timeout=5)
    msi_versions = get_msi_versions(vm_address)
    for msi in msi_versions:
        print 'INFO:', msi, 'is installed'
    for msi in EXPECTED_MSIS:
        if msi not in msi_versions:
            bad.append(msi+' MSI not installed')
    services = get_running_services(vm_address)
    for service in services:
        print 'TOOLS: service', service, 'running'
    for service in EXPECTED_SERVICES:
        if service not in services:
            bad.append(service+' not running')
    if bad == []:
        return
    message = ('tools not considered installed at this point because '+
               ' and '.join(bad))
    print 'INSTALL_TOOLS:', message
    return message
 
def get_width(vm_address):
    """Return CPU width of vm_addresss"""
    try:
        result = call_exec_daemon('getEnvVar', ['ProgramFiles(x86)'],
                                  host=vm_address)
    except Fault:
        return 32
    else:
        return 64 if '\\' in result else 32

def tools_service(service, vm_address):
    try:
        services = get_running_services(vm_address)
        for s in services:
            if service in s:
                return True
        return False
    except:
        pass


def launch_installer(dut, guest, vm_address, traditional, tools_iso_drive):
    """Launch installer, grab logs and reboot the required number of times"""

    width = get_width(vm_address)
    domain = find_domain(dut, guest)
    try:
        if traditional:
            print 'INFO: running tools installer'
            # TODO: use an in if construct to make this clearer
            run_via_exec_daemon([(XENSETUP_PATH_PATTERN % tools_iso_drive),
                                 '/S', '/norestart'], timeout=3600, 
                                host=vm_address)
            command2 = [(XENCLIENT_TOOLS_PATTERN[width] % tools_iso_drive),
                        '/passive', '/norestart', '/L*v', TOOLS_LOG_FILE]
            print 'INFO: running install stage 2', command2
            exitcode, _ = run_via_exec_daemon(command2,
                timeout=3600, host=vm_address, ignore_failure=True)
            print 'INFO: XenClientTools.msi exited with code', exitcode

            if exitcode not in [0, 3010]:
                raise UnableToInstallTools(
                    'unexpected exit code', exitcode,
                    'from XenClientTools.msi')
        else:
            unattended_bat = UNATTENDED_PATH_PATTERN % (tools_iso_drive)
            call_exec_daemon('run', [unattended_bat, TOOLS_LOG_FILE],
                             host=vm_address)
            wait_for_guest_to_start(dut, domain['name'])

    finally:
        for sub_old, sub_new in [(None, None), ('.txt', '*.msi.txt')]:
            globp = (TOOLS_LOG_FILE if sub_old is None else
                     TOOLS_LOG_FILE.replace(sub_old, sub_new))
            print 'INFO: searching for logs matching', globp
            for globo in call_exec_daemon('globPattern', [globp],
                                          host=vm_address):
                print 'INFO: reading glob', globo
                try:
                    logf = call_exec_daemon('readFile', [globo],
                                            host=vm_address)
                except Fault, exc:
                    print 'INFO: got', exc, 'reading', TOOLS_LOG_FILE
                else:
                    log = ''.join(x for x in logf.data if ord(x) > 0 and
                                  ord(x) < 128 and x != '\r')
                    print 'INFO: read', TOOLS_LOG_FILE, 'size', len(log)
                    okay = False
                    for line in log.split('\n'):
                        if line:
                            print 'TOOLS:', globo, line
                        if 'Installation completed successfully' in line:
                            okay = True
                    del log
                    del logf
                if traditional and globo == TOOLS_LOG_FILE and not okay:
                    raise UnableToInstallTools(
                        'no success line in log file from XenClientTools')
    print 'HEADLINE: MSI install completed cleanly'

    def check_service(service):
        while (not tools_service(service, vm_address)):
            sleep(20)
        print 'INFO: Found %s service running.' % service
        print 'INFO: doing reboot'
        reboot_windows(dut, domain, vm_address)
        print 'INFO: done reboot, waiting for VM to come back up'
        run(['xec-vm', '-n', domain['name'], 'switch'], host=dut)
        print 'INFO: waiting for windows to boot'
        wait_for_windows(dut, guest)
        print 'HEADLINE: done reboot'

    check_service("Citrix Tools")
    check_service("OpenXT Xen Guest")


def install_dev_certs(dut, dev, domain, vm_address):
    """Installing dev certs is critical to properly installing tools
        on 64 bit machines."""
    try:
        run_via_exec_daemon(['bcdedit','/set', 'testsigning', 'on'], host=vm_address)
        reboot_windows(dut, domain, vm_address)
        wait_for_windows(dut, domain['name'])
        call_exec_daemon('fetchFile', ['http://openxt.ainfosec.com/certificates/windows/developer.cer', 'C:\\Users\\bvt\\developer.cer'], host=vm_address, timeout=300)
        run_via_exec_daemon(['certutil -addstore -f "Root" C:\\Users\\bvt\\developer.cer'], host=vm_address)
        run_via_exec_daemon(['certutil -addstore -f "TrustedPublisher" C:\\Users\\bvt\\developer.cer'], host=vm_address)
    except Exception:
        print "ERROR: Failure to install developer certs."
        print_exc()
        raise DevCertFailureException()

def install_tools(dut, guest):
    """Install tools on guest on dut"""
    domain = find_domain(dut, guest)
    start_vm_if_not_running(dut, domain['name'])
    print 'INSTALL_TOOLS: installing tools on', domain
    vm_address = wait_for_windows(dut, guest)
    print 'HEADLINE: contacted', guest, 'and checking for tools'
    if tools_install_problems(dut, guest) is None:
        raise ToolsAlreadyInstalled(dut, guest, vm_address)

    install_dotnet(dut, vm_address, guest)

    tools_iso_drive = make_tools_iso_available(dut, vm_address, guest,
                                               domain)
    print 'HEADLINE: tools ISO available on', tools_iso_drive

    domain = find_domain(dut, guest)
    start_vm_if_not_running(dut, domain['name'])
    ensure_stable(vm_address, 30, description=guest+' on '+dut)
    unattended_bat = UNATTENDED_PATH_PATTERN % (tools_iso_drive)
    print 'INFO: checking for %s on tools CD' % (unattended_bat)
    traditional = not call_exec_daemon('fileExists', [unattended_bat],
                                       host=vm_address)
    # TODO: do we need prompt remover on XP for new (non-traditional) installer?
    attended = traditional or 'xp' in guest
    prompt_remover_control = None

    install_dev_certs(dut, guest, domain, vm_address)

    if attended:
        prompt_remover_control = (start_prompt_remover(vm_address))
        # TODO: run ensure_stable unconditinally i.e. for unattend install as well
        ensure_stable(vm_address, 60, description=guest+' on '+dut)
        print 'INFO: prompt remover started'
    try:
        if not tools_install_problems(dut, guest):
            print 'INFO: tools install already okay for', dut, guest
        else:
            launch_installer(dut, guest, vm_address, traditional,
                             tools_iso_drive)
    finally:
        if attended:
            stop_prompt_remover(prompt_remover_control, vm_address)
    print 'INSTALL_TOOLS:', domain, 'tools installation complete'
    ensure_stable(vm_address, 30, description=guest+' on '+dut)
    print call_exec_daemon('ps', [], host=vm_address)
    problems = tools_install_problems(dut, guest)
    if problems:
        print 'HEADLINE:', problems
        raise UnableToInstallTools(problems)
    print 'HEADLINE: tools installed correctly on', guest, 'at', vm_address

def futile(dut, guest, os_name, build, domlist):
    """Would it be futile to install tools?"""
    try:
        if not tools_install_problems(dut, guest):
            return "already have tools installed"
    except Exception, exc:
        print 'INSTALL_TOOLS: unable to determine if tools install, exception', repr(exc)
        print_exc()
        return "unable to interact with windows VM"
    else:
        print 'INSTALL_TOOLS: tools need to be installed on', dut, guest
