overview
========

bvt.git is a library of system test code for OpenXT, together with two main command line interfaces:

* experiments.py which runs a set of tests specified on the command line 
* launch.py which figures out which test to run next in an automated sequence

dependencies
============

* postgresql
* Python2.6
* Twisted 10.0 (TODO: confirm still used)
* Conch
* stan
* psycopg2 2.2.1 or later. earlier versions have relevant bugs
* datatables 1.6.2 (see http://datatables.net/releases/dataTables-1.6.2.zip)
* pyasn1

TFTP server configuration
=========================

Autotest needs control of a standard Linux TFTP server in order to
support automated installation of XenClient (and installer status
reports).


Installation
============

1. Create a user "autotest" on the TFTP server 
2. On the autotest machine:
    ssh-keygen
     type "/scratch/credentials/id_rsa_tftp" when prompted for key location3
3. Set up key based SSH access to the autotest account on the TFTP server. As that user:
     mkdir -p ~autotest/.ssh
     chmod 700 ~autotest/.ssh
4. Transfer /scratch/credentials/id_rsa_tftp.pub made above and append it to ~autotest/.ssh/authorized_keys

[lots more detail to be added here]

adding a machine to the BVT automated test pool
===============================================

(assuming you have all the infrastructure set up)

Give machine a name and DNS record
----------------------------------

This will be site specific.

Configure BIOS
--------------

* Boot from local disk by default
* Power on with AC
* Enable AMT

Configure AMT
-------------

* Set password to a well known password (the default AMT password is admin)
* Set host name to laptop name
* Set domain name to your site local domain name
* Ensure DHCP code enabled
* Set ME on S0, ME wake in S3, S4-5 (AC only)
* Select "Activate network" in ME control

Label the machine
-----------------

You may wisht to mke a sticker with the name on the top left of the screen and 
on the lid next to the label tag.

Connect machine
---------------

* Connect to your network
* Connect power supply (label mains connector with manufacturer)

Configure PXE server 
--------------------

Set the duts document for that machine in the mongo database
------------------------------------------------------------

* set control_machine column to autotest-2 in Cambridge or the name of your autotest server on another site
* set power column to manual or AMT (elsewhere or if statedb is not working). 
* (optional) sort out sympathy serial logging and set serial to something like "igor:s2.1" where igor is the sympathy host and s2.1 is the socket name
* clear BVT flag (we are still testing it)
* clear publish flag (we do not yet trust the results)
* hit change

Test machine completes a PXE install correctly and commision it
---------------------------------------------------------------
 
* on autotest run:
    experiments $TESTMACHINENAME -X
* make sure it completes cleanly
* In the DUTS record set BVT flag (we are ready for tests to run automatically), and set publish flag (we think the results are ready for inclusion in reports. If you are not confident in the machine being configured correctly you may want to leave this flag off for a while).  hit change

You should see results appear after a few minutes for your machine in your results database or logging. They will still appear but with the test description grayed out if you did not set the publish flag.

Mongo database convention
=========================

Mongodb is schemaless so this simply describes the convention this source code expect.

Here we present documents that look like documents in the database in Python
syntax, but use strings to describe the values rather than the values themselves.

Everything is in the "autotest" database aparts from the logs documents
which are in the "logs" database and the heads, revisions and updates data
which is in the "trackgit" database.

boot_time
---------

     {
       # mandatory
       '_id'       : 'synthetic mongo ID',
       'dut'       : 'Name of test physical machine'
       'build'     : 'Name of build, e.g. cam-oeprod-122725-master',
       'time'      : 'Build time'
       'value'     : 'floating point boot time in secodns'
     }

builds
------

     {
       # mandatory
       '_id'     : 'git tag name',
       'build_id': 'numeric build ID in tag',
       'build_type' : 'e.g. oedev or oetest',
       'branch'  : 'git branch',
       'tag_time': 'epoch timestamp when tag was created',
       'blame'   : 'list of people who contribute commits that triggered this build',
       'commits' : 'list of (short name:repo string, cgit url[, commit message]) for each commit that triggered this build. The commit message is present in newer results',
       # optional  
       'tests': {
	 'passes': number of test passes,
	 'failures': number of non-infrastructure test failures,
	 'total_cases': number of test cases,
	 'run_cases': number of test cases that have passed
       }
       'test_status':  ['epoch time', 'DUT', 'text']
       'platform': {
	   'build_time'     : 'epoch timestamp when build was created, if that happened',
	   'buildbot_number': 'buildbot sequence number',
	   'buildbot_url'   : 'buildbot url to the build result summary',
	   'eta_time'       : 'when the build system thinks the build will complete',
	   'failure'        : 'english text describing reason for build failure',
	   'status'         : 'english text describing build status',
	   'failure_log_url': 'URL for failure stdio log on buildbot',
       } 
       'site': 'site of build e.g. cam',
       'synchronizer': ... similar subrecord to platform
       'tests':  {
	  'passes': 'number of BVT passes', 
	  'failures': 'number of BVT failures,
	  'in_progress' : 'number of BVT tests running'},
       'failure_specimens': {
	   'test case 1' : 'copy of result record',
	   'test case 2' : 'copy of result record'
	},
       'failure_email': 'set to a specific value when an email failure has been sent',
       'releases': 'if set, a list of release names for this build'
     }

bvt/monitor_builds.py populates this.

classifiers
-----------

     {
       # mandatory
       'whiteboard' : 'whiteboard text to set when classifier triggers',
       'owner': 'person who is current responsible for the accuracy of this classifier, e.g. "Dickon Reed <dickon.reed@example.com>"',

       # optional
       'result_id' : 'foreign key to results._id where this classifier specifically applies',
       'failure_regexp' : 'regular expression matching failure string',
       'test_case_regexp' : 'regular expression matching test description'
       'dut_regexp' : 'regular expression matching dut',
       'earliest_build': 'earliest build date that is appropriate'
     }

Created and updated by hand from the mongo shell. Processed by bvtlib.count_results.count_results.

dut_changes
-----------

     {
      # mandatory
      'dut' : 'the dut that was changed',
      'epoch': 'epoch seconds when change happen',
      'hostname': 'machine where change made',
      'pid': 'process which made change',
      'uid': 'user ID which made change',
      'localtime': 'local time when change was made'
     }

Updated by control_automation.

duts
----

    { 
      # mandatory
      '_id': 'ID of test machine (labelling system ID if there is one else muppet name)'

      # optional
      'branches' : 'list of branches to test',
      'tag_regexp' : 'if specified tag must match this regexp; overrides branches',
      'mem': 'megabytes of RAM in the machine',
      'run_bvt' : '1 if BVT should be run when machine is idle, has no relevant queued jobs, and has a null owner field. 0 if BVT should never be run automatically on this machine.',
      'owner' : 'name of person who owns machine; if set, do not use for automatic test launches',
      'source_tree' : 'source tree on server to be used for automation',
      'install_branch' : 'branch to test on this machine',
      'last_launch_time' : 'epoch timestamp when test last started',
      'last_kick_time' : 'last time monitor_builds restarted the test automation',
      'last_finish_time': 'epoch timestamp when test last finished'
      'name': 'short name of device under test'
      'control_machine': 'machine used for automated testing for this machine',
      'power_control' : 'AMT or franken3 or similar',
      'control_pid' : 'process currently running automated test for this machine',
      'owner': 'Name of person currently owning the machine',
      'experiments':'Instead of running BVT, run experiments.py with these options',
      'development_mode': 'If set, exclude results on this dut from all reports',
      'result_id':'ID of current test in progress', 
      'notes':'text field describing stuff about machine',
      'control_command_line':'command line controlling machine'
      'test_failed':'set to true when a test has failed; removed when a fresh installation is done',
      'reactivation_time':'if set, do not run tests until this epoch time has passed. Used to prevent busy looping on rapidly failing tests'
      'serial_port':'host:sympathy socket number e.g. igor:s1-1'
      'platform' : 'chipset generation, e.g. "calpella"'
    }

jobs
----

    {
     # mandatory
     '_id' : 'synthetic mongo ID',
     'user': 'email address of person who submitted job',
     'command': 'command to run, with -m added for dut name, e.g. ["experiments", "-n"],
     'timeout': 'maximum run time of test, in seconds (e.g. 600)',
     'status' : ' "queued" if waiting or "running on ladytwo" if running on a specific mahcine', 
     'control_pid' : 'process ID of launch process'
     'dut': 'dut ID to run on, or None',
     'submit_time': 'epoch seconds when job was submitted',
     # optional
     'launch_time': 'epoch seconds when job was launched',
     'finish_time' : 'epoch seconds since job finsihed'
    }

names
-----

    { 
     # mandatory
     _id: 'FQDN to use',
     site: 'site name, e.g. CAMBRIDGE',
     allocation_time: 'time name last used'
     release_time: 'time lease on name expires',
     access_time: 'time name last referenced',
     # optional
     purpose: 'purpose to use name for, e.g. synchronizer-cam-oeprod-123456-master',
    }

slow
----

    {
     # mandatory
     'kind': 'english describing database access type',
     'start_time': 'epoch seconds when access started',
     'run_time': 'seconds taken to do access',

     # optional
     'constraints': 'constraint string'
    }

releases
--------

    { 
      # mandatory
      '_id' : 'release name e.g Glenn-XT-3.0.1-RC4'
      'build': 'e.g. cam-oeprod-130270-release-glenn-sp1'
    }

results
-------

    { 
      # mandatory
      '_id' : 'synthetic mongo ID',
      'start_time' : 'epoch timestamp of test start',

      # optional
      'build' : 'build name, e.g. "cam-oeprod-123450-mater"',
      'end_time : 'epoch timestmap of test end'
      'dut' : 'dut _id for this test',
      'dut_name' : 'dut name for this test',
      'git_id' : 'git version ID of source code of automation used for test',
      'test_case' : 'descrption of test case, or the command line if that is not known'
      'failure' : 'failure desription; test is deemed failed if this exists. Do not set for tests that pass'
      'whiteboard': 'english text describing problem'
      'infrastructure_problem': 'this problem is with infrastructure rather than product'
      'development_mode': 'copied from the duts record if defined when the test happened. If this is set, exclude this result from reports'
      'exception': 'the name of an exception which created a failure'
    }
    db.results.ensureIndex({'end_time':1})
    db.results.ensureIndex({'build':1})
    db.results.ensureIndex({'infrastructure_problem':1}) # for bvt.git/count.py
    db.results.ensureIndex({'failure':1}) # for bvt.git/count.py


Note that maybe 'command_line' should exist as distinct from 'test_case'.

results_highwater
-----------------

    { 
      'highwater' : 'epoch timestamp of the latest record added to the coverage collection'
    }

There should be zero or one documents in this collection.

test_cases
----------

    {
      '_id': 'non-negative sequential integer from 0'
      'description': 'english description of the test case'.
      'ignored_for_completion_count': '1 if the test case should be excluded from coverage analysis'
      'platform': True iff a platform (i.e. test device) is needed for this test
    }

logs
----


Note: there is so much throughput in this collection that this is stored in logs mongo database, in a capped collection.
 
    db.createCollection("logs", {capped:true, size:1000*1000*1000*10})
    db.logs.ensureIndex({result_id:1})
    db.logs.ensureIndex({dut_name:1}) 
    { 
      # mandatory
      '_id' : 'synthetic mongo ID',
      'message': 'test message in English',
      'kind': 'one english word describing message type, e.g. HEADLINE or PROBLEM',
      'time': 'epoch timestamp fo log entry'
      #optional
      'result_id' : '_id of results collection document associated with this log entry',
      'job_id' : '_id of jobs collection document associated with log entry',
      'dut_name': 'name of dut associated with log entry',
      'dut_id': '_id of dut associated with log entry'
     }



heads
-----
(in the trackgit database)

revisions
---------
(in the trackgit database)

    { 
     # mandaotry
      'repository': 'repository path',
      'revision': 'full revision hash',
      'author': 'person who did commit',
      'commit_timestamp': 'epoch time of commit'
      'timestamp': 'epoch time of push',
     #optional
      'tag': 'tag name' 
    }

updates
-------
(in the trackgit database)

    {
     # manadtory
      '_id' : 'synthetic  mongo ID',
      'action' : 'english description of udpate',

      # optional
      'repository': 'repository path affected'
      'revision' :    'revision affected'
      'result_id' : 'result_id affected'
    }

