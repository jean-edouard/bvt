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

"""A customisable set of constants

You may get local behaviour by either by putting a module called 
private_settings where Python can find it which
overrides stuff in here.

By the way, "from settings import *"  would probably be considered bad style.
Instead do something like :
   "from bvtlib.settings import PXE_DIR, BUILDS_URL instead".

"""

from os.path import split, join, abspath

#
# mongo database configuration
#
MONGODB_HOST = None # set to list of BVT database hosts; one is sufficient
MONGODB_DATABASE = 'autotest' # mongodb main database name
LOGGING_DATABASE = 'logs' # mongodb logging database name
TRACK_DATABASE = 'trackgit' # mongodb git tracking database name

#
# PXE interfacing
#
# set to filesystem location on BVT server of the PXE boot directory tree
# only needed if you want BVT to be able to PXE install operating systems
PXE_DIR = '' 
PXE_SERVER = None # if None, assume local access to PXE. Otherwise connect to that machine.

#
# Build detection
#
# If you want poller.py to detect builds which can be PXE installed then set
# BUILD_SERVER to a machine to inspect the PXE builds from

BUILD_SERVER = None
# If you want poller.py to detect tags set MONITORED_REPOSITORY to a git
# repository location to look at for tags
MONITORED_REPOSITORY = None
MONITORED_LOCATION = '/tmp/repositories' # where to store a local clone of the monitored repository
# If you want poller.py to integrate with buildbot, please review the code in poller.py and initialise
# the next few constants as appropriate
XENCLIENT_JSON_BUILDER = None  # JSON record URL string format accepting the builder name and build number
XENCLIENT_BUILDER_FORMAT = None # user URL string format accepting the builder name and build number
BUILDBOT2_BUILDER_FORMAT = None # alternative user URL string format accepting the builder name and build number
BUILDBOT2_BUILDER_URL = None # user URL string format for a specific builder 
BUILDBOT2_ALL_BUILDERS_URL = None # user URL for top level builders control
BUILDBOT2_BUILD_URL = None # user URL format for specific URL, accepting the builder name and build number

# git repository locations for:
#   - the web interface which can cross reference to git repositories
#   - bvtlib/syncxt_test.py which checks out source code
GIT_REPOSITORY_URL_FORMAT = None # git repository reference string format taking the repository name for interpolation
GIT_COMMIT_URL_FORMAT = None # git commit web interface URL taking repository name and commit ID for interpolation

# string format used in web interface for cross referncing to opengrok
OPENGROK_URL_FORMAT = None # URL format taking repository and file for interpolation

#
# Arifact storage
#
# BVT can store files such as VHDs of installed operating systems and 
# dbus logs while runnning tests. It does so over rsync, and if you want
# activate this set ARTIFACTS_ROOT to a valid rsync target from the test machine
ARTIFACTS_ROOT = None
# also set ARTIFACTS_NFS_PATH to where the output directory can be accessed over NFS
ARTIFACTS_NFS_PATH = None
ARTIFACTS_DBUS_SECTION = 'dbus-logs' # directory name for dbus logs; no need to change

# change report directory, used only for web interface
CHANGE_REPORT_DIRECTORY = None # directory path format with interpolated branch and tag

# location of license file, used for a specific test bvtlib/license_check.py only
# the test checks that each package in XT has a declared source license, i.e.
# non marked unknown, and we do this by extracting a record from the build
LICENSE_PATH = None # file path format for license file from OE, interpolated with branch and tag

# location of update directory for syncXT over the air update tests
UPDATE_PATH = None # file path format for over the air update directory, interpolate with branch, tag and build-type

XCLICIMPRPM_GLOB = None # glob format for the xclicimp RPMs with interpolated branch and tag

#
# Configugration for update_dut_recoreds.py program which is optional and only useful if 
# using an asset tracking system with the appropriate file format
#
ASSETS_BY_MAC = None # Filename format interpolate with mac address and information type
MAC_LINKS = None # directory tree location of symlinks based on MAC address
DHCP_SERVERS = [] # DHCP servers to inspect
USE_STATEDB_FOR_DHCP = True

#
# Configuration of BVT specific to the layout of the XT tools ISO
#
UNATTENDED_PATH_PATTERN = '%s:\\windows\\unattendedInstall.bat' # string format for the unattended install batch file in windows tool, interpolated with the tools ISO drive
XENSETUP_PATH_PATTERN = '%s:\\Packages\\xensetup.exe' # string format for xensetup.exe, interpolated with the tools ISO drive
XENCLIENT_TOOLS_PATTERN = {32:'%s:\\Packages\\XenClientTools.msi',
                           64:'%s:\\Packages\\XenClientTools64.msi'}  # location of MSIs for different bit widths, interpolated with the tools ISO drive
DOTNET4SETUP_PATH_PATTERN = '%s:\\dotNetFx40_Full_x86_x64.exe' # location of .net install,er interpolate with the tools ISO drive
DOTNET_4_KEY = r'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full'
DOTNET_4_NAME = 'Version'
DOTNET_4_0_INSTALLER_URL = 'http://www.cam.xci-test.com/xc_dist/distrib/dotnet/dotNetFx40_Full_x86_x64.exe'
TOOLS_LOG_FILE = 'C:\\toolsinstall.txt' # defualt location to put tools log file
EXPECTED_MSIS = ['Citrix XenClient Tools'] # a list of the MSIs we expect the Windows tools to install
EXPECTED_SERVICES = ['Citrix USB Service', 'Citrix Xen Guest Services', 
                     'Citrix Tools for Virtual Machines Service',
                     'Citrix Diagnostic Facility COM Server'] # a list of the services we expect the Windows tools to install

# 
# binary depedency URLs
#
NETPERF_LINUX_DISTRIBUTION_URL = None # URL for netperf linux binaries
NETPERF_WINDOWS_DISTRIBUTION_URL = None # URL for netperf windows binaries
AUTOIT_TAR_URL = None # URL for autoit mirror used for automated windows tools installation

#
# Windows remote control
#
EXEC_DAEMON_URL_FORMAT = 'http://%s:8936' # URL format for exec daemon, interpolated with host name of VM

AMTTOOL = 'amttool'
AMTTERM = 'amtterm'
AMTENV = {'AMT_PASSWORD' : 'XXX'}

USE_TFTP_INTEGRATION = True
WAIT_FOR_BOOT_TIME = 300

STATUS_REPORTS_ON_FAILURE = 'on failure'
STATUS_REPORTS_ALWAYS = 'always'
STATUS_REPORTS_NEVER = 'never'

# 
# URLs to find ISO and VHDs files
#
VHD_SANS_TOOLS_URL = None # URL format for VHD files of OS images without XT tools installed interpolated with name (the operating system name) and encrypted (which will normaly be empty but can be set to a string to specify the encryption type if there is one
VHD_WITH_TOOLS_URL = None # URL format for VHD files; see the comment on VHS_SANS_TOOLS_URL, with the additional interpolation name "build" to specify the build version of the tools (a tag)
ISO_URL = None # URL for OS ISO format interpolated with OS name

# The URLs above are used to transfer VHDs and ISOs to test machines using HTTP
# BVT can also write out VHDs after installing tools and use these paths to test for the existence of VHDs and ISOs,
# but this requires filesystem paths, so we have to specify VHD_(SANS|WITH)_TOOLS again as filesystem paths
# filenames to store VHD files after completing OS installation
# if specified these files will be populated, and if they point at the same filesystem as the URLs above
# then can be used on future tests
VHD_SANS_TOOLS_PATTERN = None # filename format for VHD files of OS images without XT tools installed interpolated with name (the operating system name) and encrypted (which will normaly be empty but can be set to a string to specify the encryption type if there is one
VHD_WITH_TOOLS_PATTERN = None # filename format for VHD files; see the comment on VHS_SANS_TOOLS_PATTERN, with the additional interpolation name "build" to specify the build version of the tools (a tag)

DEFAULT_POWER_CONTROL = 'manual'

TEST_MACHINE_DOMAIN_POSTFIX = '' # string appended to host names which do not contain a "." 

DEFAULT_LOGGING = 'HEADLINE,INFO,AVC,FAILURE,TESTCASE,PROBLEM,RESULT,CRASH,ARTIFACT,BUILD_DETAILS,ERROR,STDOUT,STDERR,TOOLS' # a comma separated list of logging types that get printed by default
MAXIMUM_VHD_AGE_DAYS = 14

# 
# partition alignment test configuration
#
MISALIGNED_PARTITION_MACHINES = [] # test machines which have misaligned partition tables so should be exempted from the partition table test
MISALIGNED_PARTITIONS_DONTCARE_REGEXP = "^/dev/td.+" # devices we should ignore when checking partition tables

#
# wifi testing configuraiton
#
ADVERTISED_ACCESS_POINTS = [] # access points to check for
NO_WIFI_MACHINES = [] # machines without wifi]

#
# XT UI image path locations
#
IMAGE_PATHS = {
    'xp': 'images/vms/001_ComputerXP_h32bit_120.png',
    'win7': 'images/vms/001_ComputerWin7_h32bit_120.png',
    'win7x64': 'images/vms/001_ComputerWin7_h32bit_120.png',
    'win7_sp1': 'images/vms/001_ComputerWin7_h32bit_120.png',
    'win7x64_sp1': 'images/vms/001_ComputerWin7_h32bit_120.png'}

ORACLE_SERVER = 'XXX' # Set to oracle server name
ORACLE_ENVIRONMENT_FILE = '/u01/app/oracle/product/11.2.0/xe/bin/oracle_env.sh' # location Oracle installs its env file
ORACLE_SERVER_SYSTEM_PASSWORD = 'XXX' # set to oracle server root password
APACHE_USER_CENTOS = "apache"
APACHE_USER_DEBIAN = 'www-data'
SYNCXT_SERVER = 'XXX' # Set to test server name
SYNCXT_SERVER_SITES_ENABLED_LOCATION = '/etc/httpd/sites-enabled'

LICENSE_SERVER = ORACLE_SERVER
# These directories should each contain a .lic file.  The number
# substituted in is the number of licenses the .lic file in that
# directory should grant
LICENSE_DIRECTORY_PARENT = '/var/lib/synchronizer/'
LICENSE_DIRECTORY = LICENSE_DIRECTORY_PARENT + 'license_sets'
LICENSE_DIRECTORY_FORMAT = LICENSE_DIRECTORY + '/%d'

# This directory should contain directories '0', '1', '2', '3', each
# of which should contain one file matching *.lic
LICENSE_SETS = None

DUT_FIELDS = ['platform', 'make', 'model', 'memory'] # columns to show in describe_dut output

TEST_PASSWORD_FILE = '/tmp/testpassword.sha256' # where to store test password
TEST_PASSWORD = 'XXX # replace with actual password'
TEST_USER = 'local'
LOCAL_PREFIX = 'localuser-'

PVM_PLATFORMS = ['Huron River', 'Calpella'] # machines where PVM mode works
NTP_SERVER = 'woking.cam.xci-test.com'

SMTP_ADDRESS = 'smtprelay.cam.xci-test.com'
BVT_LAMPS = []
RESULTS_EMAIL_SENDER = ''
RESULTS_EMAIL_RECEIVERS = []

DEFAULT_TAG_REGEXP = '.*'

XC_TOOLS_ISO = '/storage/isos/xc-tools.iso' # where the tools ISO sits in the installed image

DISK_ENCRYPTION_KEY_LENGTH = 512

VM_MEMORY_ASSUMED_OVERHEAD_MEGABYTES = 64

RELEASES_DIRECTORY = '/home/xc_releases'
BUILD_REGEXP = 'cam-oeprod-.*'

RELEASE_REGEXP = '([0-9]{4}-[0-9]{2}-[0-9]{2}-)(.*)'

CUSTOM_WALLPAPER = 'images/wallpaper/s2.png'

MEMORY_REPORTED_DIFFERENCE = 16

TOOLS_ISO_FILES = [':\\xenclient.ico', ':\\Packages\\XenClientTools.msi',':\\windows\\unattendedInstall.bat'] # files we are look for on the tools CD

VM_RUN_PROPERTIES = ["run-post-create", "run-pre-delete", "run-pre-boot", "run-insteadof-start", "run-on-state-change", "run-on-acpi-state-change"]

ARCHIVE_NEW_OS_INSTALL_VHDS = True
ARCHIVE_TOOLS_INSTALLED_VHDS = True
ARCHIVE_NETWORK_TEST_VHDS = True

IRC_PASSWORD = 'XXX' # password for IRC server, only used for serverlib 

#
# integration with postgresql based site administration system
# This is used for integration with specific DHCP services
# (and for bvt.git/allocate_ip_address.py which is site specific)
#
DATABASE_CREDENTIALS = {
    'assetdb': {'host':'setme.example.com', 'pwd':'XXX'},
    'statedb' : {'host':'setme.example.com', 'pwd': 'XXX'},
    'configdb': {'host':'setme.example.com', 'pwd': 'XXX'}}

DJANGO_PASSWORD = None
DJANGO_SECRET_KEY = None
DJANGO_ADMINS = []

#
# password hash and recovery key for installer answerfiles
#
PASSWORD_HASH = 'setme'
RECOVERY_PUBLIC_KEY = 'setme'
RECOVERY_PRIVATE_KEY = 'setme'

# ADD NEW DECLARATIONS HERE

# You will need to override some settings here, so rather than force users
# to modify this file we require everyone have a private_settings.py file
from private_settings import *

# DO NOT ADD DECLARATIONS HERE; add them before the private_settings block above

assert SYNCXT_SERVER != 'XXX'
