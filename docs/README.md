Overview
========

This file will serve as the initial version of documentation for BVT.  It will contain useful information regarding environment setup, the BVT "API", automated testing configuration, and code and useage examples.  This file will be subject to frequent updates as new tests, features, and fixes are implemented.


BVT (Build Validation Testing) is a automation framework designed to perform regression and functional tests on builds of OpenXT.  It can also be used as an automation tool to perform various tasks such as automatically installing OpenXT, creating a new VM, deleting a VM, installing windows tools, and starting/stopping VMs.  Basic usage of BVT requires a simple SSH connection to the device under test (DUT), but more advanced features require extra utilities such as a DHCP server, TFTP/PXE server, and a MongoDB instance.  These extra utilities allow BVT to function fully as an automated testing platform.  Specific details on installation and configuration are provided below.

Table of Contents
=================

1. Configuration
  a. TFTP
  b. Apache
  c. bvt
  d. windows guests
2. install-deps script
3. Basic Usage
4. Writing Your Own Test
5. Autotest Configuration
6. BVT Web Interface
7. API
8. How-to's
9. Advanced BVT Usage

Configuration
=============

You will need the following installed on your machine to use the full set of BVT features:


### TFTP and PXE

BVT needs control of a TFTP server to do automated PXE installs of OpenXT builds.  This TFTP server should be hosted on the same machine that hosts BVT.  When BVT automatically installs a build of OpenXT, it generates and copies a unique pxe defaults file to your pxe-root/autotest.  When the test machine eventually performs a network boot, it will connect to this TFTP server and pull down the necessary files to PXE boot the OpenXT installer.
  
### Apache (for Answer Files and Packages)

Running an Apache web server is not required, but it provides a useful repository to make tools available to your test machines.  Hosting vhds, windows MSIs/binaries, and ISOs are just a few examples of resources that are handy for both automation and testing.  Additionally, if you wish to expand the capabilities of the PXE server so that it can be utilized outside of BVT, the Apache server can host installer answer files and packages.

### BVT settings

In the bvtlib/ directory there is a file called _settings.py_.  It contains several global variables that BVT will need to execute certain tests.  The file is documented, so please refer to it for additional explanation.

When a particular setting needs to be overridden or added, the default policy is to create a _private_settings.py_ file in the same directory.  Simply add a new global constant or reassign a value to an existing one.  _private_settings.py_ is not tracked in git; it should be used a tool to personalize your BVT instance for your own environment.  

### Windows Guests and Execdaemon

One of the primary use cases for OpenXT users is the ability to run virtual instances of Windows.  Therefore, BVT must provide testcases to ensure that Windows VMs function properly on a given build of OpenXT.  However, communicating with a Windows VM is difficult; a freshly installed instance of Linux can be controlled over ssh, but the same cannot be said of Windows.  This is where the Execdaemon comes in handy.

Execdaemon sets up an XML-RPC server to communicate with BVT.  Once this server is running, we can send commands to manipulate the Windows VM.  Execdaemon requires the Windows VM to have Python 2.7 and pywin32 libraries installed.  Additionally, it is useful to add a shortcut to Startup so the execdaemon is launched when the Windows VM starts.


install-deps
============

This tool runs a series of scripts designed to download, install, and configure dependencies required by BVT.  Not all the steps are mandatory, and _install-deps_ will prompt the user to either install or skip any optional packages.

* setup/00-install-prereqs.sh  - All required BVT packages.  Cannot be skipped.
* setup/01-install-tftp-pxe.sh - Installation/Configuration of TFTP and PXE. Required for automated OpenXT installs, otherwise optional.
* setup/02-install-apache.sh   - Installs apache web server.  Optional, but useful.
* setup/03-install-dhcp-serv.sh - Installs and configures isc-dhcp-server. Not needed if the user has control of a dhcp server already. If not, very useful for a large number of testcases. Allows BVT to query for IPs of guest VMs so it can run tests from inside guests.
* setup/04-install-mms.sh      - Installs Mongo Management Studio. Completely optional, but very useful tool.
* setup/05-install-mail.sh     - Installs mailutils and postfix. Optional, but enables functionality in bvt/src/bvtlib/email_results.py.
* setup/06-setup-nodes.sh      - Creates specified number of 0 length files in bvt/nodes/. The autolaunch script uses filelocks to guarantee concurrency between testing nodes.
* setup/07-init-mongo.sh      - Calls the mongo-init.py script, which accepts input from the user to create an initial list of DUTs and test suites.

Basic Usage
===========

Existing test cases are run via the command line through the python script _bvt.py_ in the 
following manner:

```
./bvt.py <options>
```
To display a list of available commands:

```
./bvt.py -h
```
To display information about a specific testcase, including expected arguments:

```
./bvt.py -h <testcase>
```
The script will check for and verify that all the mount points exist for the OpenXT install on 
machine located at <test machine>:

```
./bvt.py -m <test machine> check_mounts
```



Writing Your Own Tests
======================

When invoking commands through bvt.py is insufficient, whether it is because the test does
not yet exist, or because some unique combination of existing functionality is desired, you will
have to write your own test.  Ideally you have some degree of Python knowledge, but you dont need 
to be proficient in the language to write a test.  What you do need is knowledge about how BVT 
recognizes and invokes test cases.

* Create a new .py file in src/testcases.  Name it something unique.
* You will need minimally three things to write a test case: import statements that give you access
	to the BVT API, an entry function called 'entry_fn', and a function called 'desc' that simply returns a string description of the testcase.
* Good import convention dictates that module imports should be limited to only what you need. 
	For example, instead of

	```python
	from bvtlib import *
	```
	strive to adhere to

	```python
	from bvtlib.run import run
	from bvtlib.wait_to_come_up import check_up
	from bvtlib.install_guest import download_image
	from os.path import isfile, isabs
	...
	```
* entry_fn is the function that will be called when you invoke ./bvt.py <testcase>
* bvt.py uses dynamic module loading and introspection to load, verify arguments, and launch a specific test case. This method is preferrable to the previous method of a master dictionary.  Simply creating the test case with the proper functions in the src/testcases directory is sufficient for bvt.py to load the module when given the module name on the commandline. It is also possible to write multiple test cases in a single module.  Either configure the entry function to invoke them all or use the --mode parameter to provide a switch for specific testcase invocation.


Autotest Configuration
======================
All of the following sections should be configured on the machine that will be running the automated testing version of BVT. In most cases, this machine will be a link between your subnet and your larger network and will need to provide things like vhds, scripts, PXE install targets, etc. that BVT will need to run its automated tests on your testing nodes.

## Requirements

* DHCP server
* PXE/TFTP server
* Apache server
* Mongodb and pymongo
* AMT

### DHCP Server
Any DHCP server may be used, my current setup uses the isc-dhcp-server.  It is recommended to run this server on a separate subnet as you will need full control over the configuration and deployment of the server.  If this is the case, using a separate NIC is advised. Follow the typical steps for the setup and configuration of your server.

Use the /etc/hosts file to alias static IPs to test machines names.

### PXE/TFTP Server
See the above section.

### Apache Server 
See the above section.

### Mongodb
Mongodb is a JSON-oriented database that is very flexible.  While BVT can be run as a standlone utility on the commandline, Mongodb greatly increases its capabilities as an automated testing framework.  apt-get install mongodb to install the database.  apt-get install python-pymongo to install the libraries to talk to mongodb from a Python module.  The following sections will describe how BVT uses mongodb to facilitate its automated testing.  It is supplementary to the 'schema' information in the main BVT README file in the root directory.  The primary database is the 'autotest' database.

First, mongodb will maintain a list of DUTs (Devices Under Test).  These are your testing nodes.  When you invoke the autolaunch.py script and request *n* nodes to work with, BVT first checks to see if there are *n* nodes free (determined by a filelock acquisition).  If there are, it then queries BVT for information about those nodes (IP, MAC, power control type, etc).  Test devices should be added manually to mongodb through the use of the command line or a web interface. Work is ongoing to ease manual entry.  It should be noted that if you increase/decrease the size of your testing pool, you should add/remove the entries in the mongodb to avoid any errors.  BVT talks to the DUTs primarily over SSH, but depending on the test and power control type, it may also use Intel AMT to power on/off/reboot the test machine.  For example, PXE installing OpenXT currently requires the use of AMT so that the test node can be PXE booted or forcibly shutdown if the install is unsuccessful.  It should be noted that with VT-d enabled, passing through the NIC to the ndvm renders AMT unusable as the NIC only has access to memory allocated to the ndvm.  A special build of OpenXT is required to perform AMT operations while XT is booted.  Additionally, one may use test machines with two NICs: one for AMT control, and the other to pass through to the ndvm.  A small addition to the answerfile (to pass the secondary NIC) is required for this operation.  BVT expects the second nic to be installed on PCI bus 01 in this configuration.
 
BVT will maintain another collection inside autotest called 'suites'.  This collection enumerates all test suites that are available for use through autolaunch.py.  A test suite is a collection of related test cases that should be run sequentially to verify some criteria.  A document in this collection contains the name of the suite, the number of steps involved in the test, and a list of commands to be run through the bvt.py script.  New test suites can be added to the database but they should not be removed.  To ensure correct operation of autolaunch, please adhere to the suite schema defined in the other README.

The jobs collection has been modified to support BVT as a daemon with queued tasks, and also to support autolaunch/suite testing.

### Autotesting as a Daemon
To function properly as an automated testing platform, BVT provides a daemon that can start tests with minimal interaction.  Coupled with the scheduler presented by the web UI, jobs can be manually requested and queued without needing ssh access to the Test Controller.  The daemon portion of BVT continually polls the job collection in mongo and attempts to start any queued jobs it finds there.  If no test nodes are free, the job remains with a status of 'queued' until the requested number of nodes become available.  Once the job has been started in a subprocess, we mark it as 'running' until completion upon which results are recorded and the job is removed from the collection.

Support for this feature requires the python-daemon package (obtainable from package repositories).  Future work will involve expanding the capabilities of the bvt daemon beyond simple polling/execution tasks.  A second daemon provides support to also poll a buildbot instance for newly completed builds and support launching predetermined tests on new builds.

To use both daemons, simply issue ./controller.sh start.  build_watcher has been configured by default to query the upstream OpenXT buildbot instance located at openxt.ainfosec.com:8010.  This will begin queueing up jobs to run the suite named 'new-build-tests' on a single node from your testing pool.  This suite name has been configured by default in settings.py, override it in private_settings.py if you want to call it something else.  Once the jobs have been queued, bvt_daemon will begin executing the jobs in parallel, if there are sufficient test nodes, and storing the results in mongo.

To change the buildbot servers being queried (for example, to point to your own), override the BUILDBOT_BUILD_SERVERS variable with a new list.  Note that BVT expects the names of the builds to follow this convention: sitename-dev-buildnumber-branch.  In the case of upstream, build names look like this: lxt-dev-200-master.

 
### Buildbot Integration
BVT supports buildbot integration.  The build_watcher daemon can poll the buildbot instance for recently completed builds and update the mongo 'builds' collection to reflect this new information.  By setting ENABLE_BW_TEST to false (by default, it is True), build_watcher will only update the mongo instance.  It will not queue jobs for testing.  This functionality is useful if you want to keep your mongo instance in sync with the buildbot server but do not wish to run tests.


BVT Web Interface
=================

BVT comes with a basic web interface that provides several features.  To enable it, run webapp/manage.py runserver.  Currently, it is used to view logs, schedule tests, determine which test nodes are free, and view test results.  All other features in the web interface are not officially supported yet.  Improvement of the web front end is an excellent area for contribution to BVT.

To schedule a test, navigate to "test scheduler". In the "Command" line, issue a command using the autolaunch tool to queue a test.  Ensure the bvt_daemon is running and it will launch the queued test.  This is ideal for manually running tests without requiring ssh access to the test controller.  Currently, no form of authentication is in place to limit access to users, so be careful how you expose the test scheduler in your particular environment.

API
===

The following section will attempt to enumerate and describe the current BVT API so that new developers have access to a centralized reference when writing code for BVT.  Functions will be organized topically.

### Command Execution 

| Function | Description |
| ---- | --------------- |
| [run()](run.md#run) | Invoke and execute a subprocess locally or on a remote host. |
| [retry()](run.md#retry) | Run the command, retrying in the event of an exception. | 
| [readfile()](run.md#readfile) | Read the contents of a file located on a remote host. |
| [writefile()](run.md#writefile) | Write some data to a file located on a remote host. |
| [verify_connection()](run.md#verify_connection) | Verify that we can connect to host as user. |
| [run_via_exec_daemon()](run.md#run_via_exec_daemon) | Execute a set of arguments on a remote host running the execdaemon. |

### Guest Ops
| Function | Description |
| ---- | --------------- |
| [install_guest()](guest.md#install_guest) | Install guest on the specified host. |
| [check_free()](guest.md#check_free) | Check for sufficient free memory and disk space on remote host. |
| [download_image()](guest.md#download_image) | Download a iso or vhd to the remote host. |
| [list_cd_devices()](guest.md#list_cd_devices) | List cd devices recognized by the guest. |
| [file_exists()](guest.md#file_exists) | Checks to see if a file exists on a remote target. |
| [create_file()](guest.md#create_file) | Writes some content to a file on a remote target. |
| [make_tools_iso_available()](guest.md#make_tools_iso_available) | Present xc_tools iso to the guest. |
| [soft_reboot()](guest.md#soft_reboot) | Perform soft reboot inside the guest. |
| [soft_reboot_and_wait()](guest.md#soft_reboot_and_wait) | Perform soft reboot but wait for guest to come back up. |
| [start_vm()](guest.md#start_vm) | Start the guest on the remote host. |
| [start_vm_if_not_running()](guest.md#start_vm_if_not_running) | Start the guest if it is not already running. |
| [have_driver()](guest.md#have_driver) | Checks the remote guest for the named driver. |
| [guest_start()](guest.md#guest_start) | Start the guest on the remote host. |
| [guest_shutdown()](guest.md#guest_shutdown) | Shutdown the guest on the remote host through the toolstack. |
| [guest_destroy()](guest.md#guest_destroy) | Destroy the guest on the remote host. |
| [guest_delete()](guest.md#guest_delete) | Delete the guest on the remote host. |
| [guest_uuid()](guest.md#guest_uuid) | Return the uuid of the named guest. |
| [guest_exists()](guest.md#guest_exists) | Determine if the named guest exists on the remote host. |
| [guest_state()](guest.md#guest_state) | Return the current state of the guest. |
| [create_guest()](guest.md#create_guest) | Create a new guest on the remote host. |
| [get_vm_ip()](guest.md#get_vm_ip) | Get the mac address of the guest and query our dhcp server for the assigned lease. |


### Host Ops
| Function | Description |
| ---- | --------------- |
| [check_mac_addresses()](host.md#check_mac_addresses) | Verify that the MAC addresses between eth0 and brbridged match. |
| [check_mounts()](host.md#check_mounts) | Verify that the expected mount points mounted cleanly.|
| [ConsoleMonitor()](host.md#ConsoleMonitor) | Class to enable console logging on remote host. |
| [start_logging()](host.md#start_logging) | Start logging dbus messages on remote host. |
| [stop_logging()](host.md#start_logging) | Stop logging dbus messages on remote host. |
| ~~[test_enforce_encrypted_disks()](host.md#test_enforce_encrypted_disks)~~ | Create VM with encrypted vhd, write to it, and verify that the VM does not start. |
| [FilesystemWriteAccess()](host.md#FilesystemWriteAccess) | Gain temporary rw access to a filesystem. |
| [try_get_build()](host.md#try_get_build) | Return the build information on remote host. |
| [get_xc_config()](host.md#get_xc_config) | Return the contents of the XT config on remote host. |
| [try_get_xc_config_field()](host.md#try_get_xc_config_field) | Get a field from the configuration of the remote XT machine. |
| [grep_dut_log()](host.md#grep_dut_log) | Search the rotating log on the remote host for lines containing the search pattern. |
| [network_test()](host.md#network_test) | Test network performance using the iperf utility. | 
| [partition_table_test()](host.md#partition_table_test) | Verify that all partitions are correctly aligned on a 4K boundary. |
| [set_power_state()](host.md#set_power_state) | Transition the remote machine into the specified power state. |
| [set_s5()](host.md#set_s5) | Transition remote machine to power state s5. |
| [set_s0()](host.md#set_s0) | Transition remote machine to power state s0. |
| [set_pxe_s0()](host.md#set_pxe_s0) | Transition remote machine to power state s0 and perform a pxe boot. |
| [power_cycle()](host.md#power_cycle) | Power cycle the remote machine through power control. |
| [get_power_state()](host.md#get_power_state) | Returns the current power state of the specified remote machine.
| [verify_power_state()](host.md#verify_power_state) | Verify that the remote machine is currently in the specified state. |


Advanced BVT Usage
==================

The previous sections have described the setup, configuration, and design behind BVT.  This section will provide detailed examples for running the framework.

###Running Various Testcases With bvt.py
```
./bvt.py -m test1 --guest win7 --encrypt-vhd False --mode vhd --vhd-url 192.168.1.1/vhds/win7.vhd install_guest
```
Installs a guest named "win7" from vhd downloaded from webserver hosted on 192.168.1.1 on test machine test1 (name is aliased in /etc/hosts file), and the vhd is not encrypted.

```
./bvt.py -m test1 --build /builds/lxt-dev-200-master pxe_install_xc
OR
./bvt.py -m 192.168.1.41 --build /builds/lxt-dev-200-master --mac-address 00:11:22:33:44:55 pxe_install_xc
```
The first case assumes Mongo has been configured and the DUT document test1 contains both the IP and MAC address of the test machine.  BVT will automagically retrieve that info and run the pxe_install_xc test on that machine using the valid local build tree at /builds/lxt-dev-200-master.  The second case assumes mongo is not installed, so we provide the IP and MAC address explicitly so BVT can contact the machine over the network via AMT.  We still install the build located at /builds/lxt-dev-200-master.  NOTE: this assumes that TFTP and PXE have been installed and configured.

```
./bvt.py -m test1 --guest win7 install_tools
```
Installs windows tools in the windows guest "win7".  NOTE: BVT control over a windows VM requires the VM to be "BVT-aware"; it is running the provided _execdaemon_.  

###Running Test Suites with autolaunch.py
```
./autolaunch.py -n 1 --suite install-suite --build lxt-dev-200-master --server openxt.ainfosec.com
```
Queries mongo for a test suite called "install-suite", queries the build server openxt.ainfosec.com (the upstream community build server for OpenXT) for a build named lxt-dev-200-master, downloads it to the test controller, and launches a subprocess to execute the steps defined in install-suite.  "install-suite" is a mongodb document that the user has provided.  The -n flag tells BVT to run the test on the first free test node it can find.  If we use -n 2, the test will be run simultaneously on two test nodes.

How-To's
========

### How-to do basic Automated Installs
You've installed all the dependencies and now you want to automatically install openxt.  Make sure you've done the following steps:

* Connect to the autotest db through MMS
* Create a new collection "duts" by right-clicking 'autotest' and selecting "Add collection..."
* Click Add Document and enter the following values:
* "name": name of test machine,
* "num": numeric designation of test machine in test pool (ex. 4),
* "acquired": 0,
* "enabled": 1,
* "power_control": "AMT",
* "mac-amt": mac address of onboard NIC,
* "ip-amt": static IP assigned to onboard NIC
* Click save.
* Open src/bvtlib/private_settings.py and add AMTENV = {'AMT_PASSWORD': 'your machines AMT password'}
* Also add to private_settings.py DHCP_SERVERS = ['127.0.0.1']
* edit /etc/hosts so that hostname resolves to the subnet IP you assigned to the test controller.
  for example: 192.168.1.1     bvt-master
* edit /etc/hosts to add name (suffixed with -amt) to static IP mapping for the test machine.
  for example: 192.168.1.10    test1-amt

Make sure the build you want to install is on your machine (for example, at /builds/lxt-dev-222-master), you need the netboot/ and repository/ directories.  You also need to configure AMT on your test machine.  This is done through the BIOS, and the exact steps vary for different machines.  Then run:

```
./bvt.py -m <ip of test machine> --build /builds/lxt-dev-222-master pxe_install_xc
```

### How to do Advanced Automated Installs
 
Autolaunch.py can go retrieve a build from a buildserver and then install it on your test machine if you have the right settings configured.  Perform the following steps to configure this:

Add a new test suite to mongodb
* Create the 'suites' collection if it doesn't exist
* Click Add Document.
* Enter the following information:
* "name": "install-suite",
* "steps": 1,
* "s-0": [
       "./bvt.py",
	   "pxe_install_xc"
	]

Make sure test nodes are setup
* For each 'dut' entry in mongo make sure there is a file in nodes/
* Also add to private_settings.py TEST_NODES = # of nodes (so if there are 3 testing nodes TEST_NODES = 3)

Make sure bvt knows about the build servers
* Settings.py should default to upstream openxt.ainfosec.com as the build server

```
./autolaunch.py -n 1 --build lxt-dev-223-master --server openxt.ainfosec.com --suite install-suite
```
Here we ask autolaunch to use the first available node (-n 1), retrieve build lxt-dev-223-master from openxt.ainfosec.com and launch the install-suite (which we defined in mongodb)

```
./autolaunch.py -m test1 --build lxt-dev-223-master --server openxt.ainfosec.com --suite install-suite
```
You can also specify the name of the test machine to run the test suite on with the -m flag.
