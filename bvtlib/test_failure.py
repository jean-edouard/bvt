#
# Copyright (c) 2011 Citrix Systems, Inc.
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

import twisted.python.failure, time
from bvtlib import exceptions,sleep
from twisted.internet import defer
import os, socket, psycopg2, cStringIO

def test_failure(session, dut, pause_on_failure=False):
    failure = twisted.python.failure.Failure()
    session.log('INFO','got failure',failure)
    return process_failure(session,failure,dut)

def log_failure(session, failure, context=None,log=True):
    io = cStringIO.StringIO()
    failure.printDetailedTraceback(file=io)
    if log:
        io2 = cStringIO.StringIO()
        failure.printBriefTraceback(file=io2)
        print 'FAILURE:', io2.getvalue()
    session.make_log_entry({'kind':'BACKTRACE',
                            'message': io.getvalue()})

@defer.inlineCallbacks
def process_failure(session, failure, dut, 
                    failure_string_callback=(lambda _: None)):
    if failure is not None: 
        failure_str=repr(failure.value)
        if not isinstance(failure.value, exceptions.ExternalFailure):
            failure_str = 'internal BVT bug: '+failure_str
    else: failure_str = ''
    yield session.store_failure(failure_str)
    log_failure(session, failure)
    yield failure_string_callback(failure_str)
    defer.returnValue ((failure_str, failure))
