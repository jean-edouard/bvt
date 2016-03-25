#method is based off OXT-137 repro instructions
#might as well add in linux verison as well later
#After making sure VM is running, makes it sleep from dom0
#then it makes it sleep from within VM
#then attempts to shutdown from sleep





from src.bvtlib.run import run
from time import sleep
from src.bvtlib.retry import retry
from src.bvtlib.guest_info import get_system_type, is_acpi_state, guest_acpi_state
from src.bvtlib.guest_ops import guest_destroy, guest_delete, guest_exists, guest_state, guest_shutdown, create_vm_and_snapshot
from src.bvtlib.start_vm import start_vm_if_not_running
from src.testcases.install_guest import install_guest
from src.bvtlib.install_tools_windows import install_tools
from src.bvtlib.wait_to_come_up import wait_to_come_up
from src.bvtlib.call_exec_daemon import call_exec_daemon
from src.bvtlib.windows_transitions import vm_sleep_self, vm_reinstate_hibernate, vm_poweron, vm_resume
from src.bvtlib.host_ops import get_vhd_from_url




class VMSleepFailure(Exception):
    """the VM didn't properly go into sleep mode"""

class VMResumeFailure(Exception):
    """the VM failed to resume from sleep"""

class VMShutdownFailure (Exception): 
    """the VM wouldn't shutdown"""

class VMDeletionFailure(Exception): 
    """The VM didn't get deleted"""

class URLNotSetException(Exception):
    """Required Global for set up is not set"""


def is_asleep(host,guest):
    #used to assert the host has entered the sleep state
    if is_acpi_state(host,guest,3):
        return True
    else:
        raise VMSleepFailure()

def sleep_dom0(host,guest):
    #depending on the status changing of the host before it sleep might fail first time
    retry(
        lambda: run(['xec-vm', '-n', guest, 'sleep'], host=host),
        description = 'xec-vm sleep on VM',
        timeout = 120)
    is_asleep(host,guest)

    """Wake Vm up"""
    vm_resume(host, guest)
    if is_acpi_state(host,guest,3):
        raise VMResumeFailure()

def sleep_vm_windows(host,guest):
    vm_sleep_self(host, who=guest)
    #due to use of exec-daemon in vm_sleep_self, can take time for it to finish
	
    if retry(
        lambda: is_asleep(host,guest), description = 'checking if VM is asleep yet',
        timeout = 120):
        pass
    vm_resume(host,guest)
    vm_reinstate_hibernate(host, who=guest)	
    """windows sleep commands like to go to hibernate instead, so after we done we need to reinstate them"""

def sleep_to_shutdown(host,guest):
    print "Attempting shutdown from sleep"
    run(['xec-vm', '-n', guest, 'sleep'], host=host)
    guest_shutdown(host, guest)
    if is_acpi_state(host,guest,3):
        raise VMResumeFailure()

def test_sleep(host, url):

    guest = 'sleeper'
    path = get_vhd_from_url(host, url)
    
    create_vm_and_snapshot(host, guest, "sleeper test", path, "sleeper.vhd")

    install_tools(host, guest)

    start_vm_if_not_running(dut=host, guest=guest)
    #might be off or hibernating
    vm_resume(host, guest)
    #incase it is already sleeping
    sleep_dom0(host,guest)
    os = get_system_type(host, guest)
    print 'os is ' + os
    #step 4.1 sleep from within host windows
    if os == 'windows':
        sleep_vm_windows(host,guest)
	
        #step 4.2 sleep from within host linux
    elif os == 'linux':
        print 'Linux not implemented yet'
        vm_resume(host,guest)

    else:
        raise Exception("Unexpected OS: %s" % os)
   
    #make sure it can shutdown from sleep
    sleep_to_shutdown(host,guest) 

    #step 5 clean up (delete VM) if wanted
	
    """shutdown VM so it can be deleted"""
    guest_destroy(host, guest)
    if guest_state(host,guest) == 'stopped':
        guest_delete(host, guest)
        if guest_exists(host, guest):
            raise VMDeleteionFailure()

    print 'INFO: sleep test succeeded'	

def entry_fn(dut, url):
    test_sleep(dut, url)

def desc():
    return 'Checks how it handles sleeping and certain operations'
