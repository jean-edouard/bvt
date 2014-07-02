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

"""Handle the entry point of a main function"""
import sys

from twisted.internet import reactor, error

EXIT_CODE_ACCUMULATOR = [0]
def top_level(go_function):
    """Start go_function which returns a deferred and then exit"""
    deferred = go_function()
    deferred.addErrback(grumble)
    deferred.addCallback(stop)
    if EXIT_CODE_ACCUMULATOR == [0]:
        reactor.run() # pylint: disable=E1101
    sys.exit(EXIT_CODE_ACCUMULATOR[-1])

def exit(code):
    EXIT_CODE_ACCUMULATOR.append(code)
    sys.exit(code)

def stop(val=None):
    # Give time to the reactor to schedule the last logging calls
    from time import sleep
    sleep(1)
    try:
        reactor.stop()
    except error.ReactorNotRunning:
        pass
    
def grumble(failure):
    """show error"""
    if not failure.check(SystemExit):
        failure.printTraceback()
        EXIT_CODE_ACCUMULATOR.append(1)
    else:
        EXIT_CODE_ACCUMULATOR.append(failure.value.args[0])
    stop()



