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

from os.path import exists
from json import load


class Message:
    def __init__(self, log):
        self.tokens = log.split()
        
        t = self.tokens.pop(0)
        if t == 'method':
            assert self.tokens.pop(0) == 'call'
            self.type = 'M'
        elif t == 'signal':
            self.type = 'S'
        else:
            raise Exception('Unsupported message type: %s' % t)
        
        self.__expect_param('sender')
        assert self.tokens.pop(0) == '->'
        self.__expect_param('dest')
        if self.dest == '(null': # pylint: disable=E0203
            assert self.tokens.pop(0) == 'destination)'
            self.dest = 'null'
        
        self.__expect_param('serial', int)
        self.__expect_param('path')
        self.__expect_param('interface')
        self.__expect_param('member')
        
        self.args = []
    
    def __expect_param(self, name, cast=None):
        t = self.tokens.pop(0)
        param = '%s=' % name
        assert t.startswith(param), 'expected %s, got %s' % (param, t)
        value = t.replace(param, '').rstrip(';')
        if cast is not None:
            value = cast(value)
        setattr(self, name, value)
    
    def add_arg(self, arg):
        t = arg.strip().split()
        value = ' '.join(t[1:])
        self.args.append((t[0], value))


def parse_dbus_log(lines):
    messages = []
    current_message = None
    for line in lines:
        if line.startswith('   '):
            assert current_message is not None
            current_message.add_arg(line)
        else:
            if current_message is not None:
                messages.append(current_message)
            current_message = Message(line)
    return messages


XENCLIENT = 'com.citrix.xenclient'
def print_messages(messages, is_start=None, is_end=None, filters=None,
                   known_agents=None, skip_non_xenclient=True):
    interested = is_start is None
    for msg in messages:
        if not interested:
            # We could define a start event
            if is_start is not None and is_start(msg):
                interested = True
            if not interested:
                continue
        
        # We could define an end event
        if is_end is not None and is_end(msg):
            interested = False
        
        # We could have filters
        if filters is not None:
            filtered = False
            for filter in filters:
                if filter(msg):
                    filtered = True
            if filtered:
                continue
        
        # The interface is potentially the most informative...
        if msg.interface.startswith(XENCLIENT):
            name = msg.interface
        
        # ...otherwise use the destination
        elif msg.dest.startswith(XENCLIENT):
            name = msg.dest
        
        else:
            # We could want to skip non xenclient messages
            if skip_non_xenclient:
                continue
        
        name = name.replace(XENCLIENT + '.', '')
        
        # We could know the ids of some of the agents
        if known_agents is not None and msg.sender in known_agents:
            msg.sender = known_agents[msg.sender]
        sender = '%s' % msg.sender
        
        if msg.type == 'M':
            actors = '%s -> %s' % (sender, name)
        else:
            actors = '[S] %s' % sender
        
        args = '(%s)' % (', '.join([a[1] for a in msg.args]))
        
        print '%-19s %s%s' % (actors, msg.member, args)


KNOWN_EVENTS = {
    'sync_reg': {
        'is_start': lambda msg: msg.member == 'set_registration_data',
        'is_end'  : lambda msg: (msg.member == 'auth_status' and
                                 msg.args[0][1] == '"ok"'),
        'filters' : [
            lambda msg: (msg.dest == 'com.citrix.xenclient.db' and
                         msg.member == 'read' and 'mouse' in msg.args[0][1]),
            lambda msg: msg.dest == 'com.citrix.xenclient.rpc_proxy'
        ]
    }
}


def parse_log(name, desired_event=None):
    messages = parse_dbus_log(open(name + '.log').readlines())
    
    map = None
    map_file = name + '.map'
    if exists(map_file):
        map = load(open(map_file))
    
    kargs = {'is_start':None, 'is_end':None, 'filters':None, 'known_agents':map}
    if desired_event in KNOWN_EVENTS:
        kargs.update(KNOWN_EVENTS[desired_event])
    
    print_messages(messages, **kargs)
