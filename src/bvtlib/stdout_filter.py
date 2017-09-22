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

"""Filter stdout, showing only lines beginning with DEFAULT_LOGGING 
prefixes. Also supports invoking a callback for each line of output.
"""
from src.bvtlib.settings import DEFAULT_LOGGING
from time import time
import sys

class StdoutFilter:
    """Filter stdout, showing only lines beginning with DEFAULT_LOGGING 
    prefixes. Also supports invoking a callback for each line of output."""
    def __init__(self, verbose=False, start = None):
        self.verbose = verbose
        self.start = start
        self.orig_stdout = None
        self.buffer = list()
        self.callbacks = {}
    def __enter__(self):
        if self.start is None:
            self.start = time()
        if not hasattr(sys, 'orig_stdout'):
            sys.orig_stdout = sys.stdout
        self.orig_stdout = sys.orig_stdout
        assert not isinstance(self.orig_stdout, StdoutFilter)
        sys.stdout = self
        return self
    def __exit__(self, _type, value, traceback):
        sys.stdout = self.orig_stdout
    def flush(self):
        """We autoflush so explicit flush is a no-op"""
    def write(self, data):
        """Feed line data to the logging system"""
        self.buffer.append(data)
        while self.push():
            pass
    def push(self):
        """Push a complete line in the buffer to the publish function,
        return true, or return false if there are no complete line"""
        i = 0
        for ele in self.buffer:
            index = ele.find('\n')
            if index != -1:
                self.publish(''.join(self.buffer[:i]+[self.buffer[i][:index]]))
                del self.buffer[:i]
                self.buffer[0] = self.buffer[0][index+1:]
                return True
            i += 1
    def publish(self, message):
        """Display message"""
        spl = message.split()
        if spl and spl[0].endswith(':'):
            kind = spl[0][:-1]
            message = message[len(kind)+1:]
            if message.startswith(' '):
                message = message[1:]
        else:
            kind = 'INFO'
            if len(spl) == 0: 
                return
        tstamp = time()
        delta = tstamp - self.start
        if self.verbose or kind in DEFAULT_LOGGING.split(','):
            sys.stderr.write('%.3fs %s: %s\n' % (delta, kind, message))
        for key, callback in self.callbacks.items():
            callback(tstamp, kind, message)
    def add_callback(self, key, callback):
        """Add a callback"""
        self.callbacks[key] = callback
    def del_callback(self, key):
        """Remove a callback"""
        if key in self.callbacks:
            del self.callbacks[key]

