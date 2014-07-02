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

"""IRC support for the results server. Here for lack of a better
placer"""
from twisted.words.protocols import irc
from bvtlib import Session
from bvtlib.settings import IRC_PASSWORD
import socket

EX = '-dev' if 'dev' in socket.gethostname() else ''

class MyIRCClient(irc.IRCClient):
    """Subclass for IRC client"""
    password = IRC_PASSWORD
    def __init__(self, server, nickname): 
        self.server = server
        self.nickname = str(nickname)
    def connectionMade(self):
        print 'connected'
        irc.IRCClient.connectionMade(self)
        self.server.active[self.nickname].add(self)
        while self.server.connection_waiters[self.nickname]:
            self.server.connection_waiters[self.nickname].pop().callback(self)

def say(server, nick, message, action=False):
    """announce something on a channel; server is a python objet 
    which is expected to be persistent between calls and we can stuff
    things in"""
    nick += EX
    if nick not in server.irc_con:
        server.active[nick] = set()
        server.connection_waiters[nick] = []
        server.irc_con[nick] = Session.make_proxy(
            (lambda: MyIRCClient(server, nick)), 
            ['me', 'msg'], 'irc-int.xci-test.com', 6667, 
            server.active[nick], server.connection_waiters[nick])()
        server.irc_con[nick].connect()

    irccon = server.irc_con[nick]
    func = irccon.me if action else irccon.msg
    channel = '#autotest' + EX
    func(channel, str(message))
