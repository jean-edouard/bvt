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

"""Timeouts using with statement"""
from signal import alarm, signal, SIGALRM
from time import time
import sys

class TimeoutError(Exception):
    """A function timed out"""

def alarm_handler(*_):
    """Trigger any alarms due"""
    first = None
    for tstamp in sorted(sys.deadlines.keys()):
        if tstamp > time():
            break
        deadt=sys.deadlines.pop(tstamp)
        for timer in deadt:
            if timer.timeout_callback:
                delay = time() - timer.start
                timer.timeout_callback(delay)
            if first is None:
                first = timer
    if first:
        delay = time() - first.start
        print 'TIMEOUT: triggered; earliest is', first.description, \
            'in', delay, 'seconds'
        raise TimeoutError(first.description, first.timeout, delay)
        
def set_alarm_signal():
    """Set alarm signal. Also raise any due timeouts."""
    alarm_handler()
    if sys.deadlines == {}:
        alarm(0)
        return
    earliest = list(sorted(sys.deadlines.keys()))[0]
    delay = int(earliest - time())+1
    assert delay > 0
    alarm(delay)

def time_limit(timeout, description, timeout_callback=None):
    """Run block with timeout"""
    class Wrapper:
        """with wrapper"""
        def __init__(self):
            self.start = time()
            self.timeout = timeout
            self.description = description
        def __enter__(self):
            """Start routine, with alarm printed"""
            deadline = self.start + timeout
            if not hasattr(sys, 'deadlines'):
                sys.deadlines = dict()
            self.timeout_callback = timeout_callback
            sys.deadlines.setdefault(deadline, list())
            sys.deadlines[deadline].append(self)
            signal(SIGALRM, alarm_handler)
            set_alarm_signal()
        def __exit__(self, *_):
            """End routine"""
            for tstamp in sys.deadlines.keys():
                sys.deadlines[tstamp] = [a for a in sys.deadlines[tstamp] 
                                         if a != self]
                if sys.deadlines[tstamp] == []:
                    del sys.deadlines[tstamp]
            set_alarm_signal()
    return Wrapper()
