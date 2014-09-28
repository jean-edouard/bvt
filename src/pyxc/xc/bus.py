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

from threading import Thread
from Queue import Queue, Empty
import logging as log
from time import time
from os import remove
from os.path import exists
from sys import exit, stdout
from dbus import SystemBus, Interface
from dbus.mainloop.glib import DBusGMainLoop
from gobject import MainLoop, threads_init
from syslog import syslog

# This has to be done before any connection to the bus is opened
# for this reason we execute it at the module loading time
DBusGMainLoop(set_as_default=True)


def dbus_loop(actor):
    threads_init()
    mainloop = MainLoop()
    actor.set_event_loop(mainloop)
    actor.start()
    mainloop.run()


def get_interface(service, path='/', interface=None):
    if interface is None:
        interface = service
    obj = SystemBus().get_object(service, path)
    return Interface(obj, interface)


class SignalListener:
    def __init__(self, actor, interface, name):
        self.actor = actor
        self.interface = interface
        self.name = name
        
        interface.connect_to_signal(name, self.handle)
    
    def handle(self, *args):
        log.debug('[SIGNAL] %s.%s(%s)' % (self.interface.dbus_interface,
                                        self.name, ', '.join(map(str, args))))
        self.actor.signals.put((self.interface.dbus_interface, self.name, args))


class DBusActor(Thread):
    """ Simple dbus actor performing a linear sequence of actions """
    def __init__(self):
        Thread.__init__(self)
        self.signals = Queue()
    
    def set_event_loop(self, loop):
        self.loop = loop
    
    def listen_signal(self, interface, name):
            SignalListener(self, interface, name) 
    
    def wait_signal(self, interface, name, timeout=30, condition=None):
        log.debug('Waiting for: %s.%s' % (interface, name))
        start = time()
        try:
            while True:
                t = timeout - (time()-start)
                if t <= 0:
                    break
                i, n, args = self.signals.get(block=True, timeout=t)
                if i == interface and n == name:
                    if condition is not None and not condition(args):
                        continue
                    return args
        except Empty, _:
            pass
        return None
    
    def act(self):
        """To be overridden with the  desired sequence of actions"""
        pass
    
    def run(self):
        success = self.act()
        self.loop.quit()
        exit(0 if success else 1)


class Input:
    AUTH_FLAG_REMOTE_USER = 8
    
    @staticmethod
    def get_interface():
        return get_interface('com.citrix.xenclient.input')


class Bed:
    CERT_NEED_AUTH_CODE = 503
    
    @staticmethod
    def get_device_interface():
        return get_interface('com.citrix.xenclient.bed',
                '/com/citrix/xenclient/bed', 'com.citrix.xenclient.bed.device')


class DBus:
    @staticmethod
    def get_interface():
        return get_interface('org.freedesktop.DBus', '/org/freedesktop/DBus')


def get_service_map():
    servicemap = {}
    
    dbus = DBus.get_interface()
    services = map(str, dbus.ListNames())
    
    ids = set([])
    for service in services:
        if service[0] == ':':
            ids.add(service)
        else:
            id = dbus.GetNameOwner(service)
            servicemap[id] = service
    
    # For the id without service name get the process name instead
    known = set(servicemap.keys())
    from xc.utils import cmd
    for unknown in (ids - known):
        pid = dbus.GetConnectionUnixProcessID(unknown)
        name, _, _ = cmd(['ps', '-p', str(pid), '--no-headers', '-o', '%c'])
        servicemap[unknown] = name
    
    return servicemap


class DBusConfig:
    PATH = "/etc/dbus-1/system-local.conf"
    ALLOW_EAVESDROP = """
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <policy context="default">
    <allow eavesdrop="true"/>
  </policy>
</busconfig>
    """
    
    @staticmethod
    def reload():
        log.info("Reloading dbus conf")
        dbus = DBus.get_interface()
        dbus.ReloadConfig()
    
    @staticmethod
    def allow_eavesdrop():
        if not exists(DBusConfig.PATH):
            open(DBusConfig.PATH, 'w').write(DBusConfig.ALLOW_EAVESDROP)
            DBusConfig.reload()
        log.info("Eavesdrop is allowed")
    
    @staticmethod
    def disallow_eavesdrop():
        if exists(DBusConfig.PATH):
            remove(DBusConfig.PATH)
            DBusConfig.reload()
        log.info("Eavesdrop is disallowed")


TYPE_UND, TYPE_CALL, TYPE_RETURN, TYPE_ERROR, TYPE_SIGNAL = range(5)


class MessageFieldsGetter:
    """Save 6 characters each time you want to access a message field"""
    def __init__(self, msg):
        self.msg = msg
    
    def __getattr__(self, attr):
        return getattr(self.msg, 'get_'+attr)()


class DBusLogger:
    def __init__(self, output='syslog'):
        self.services = get_service_map()
        if output == 'syslog':
            self.output = syslog
        else:
            self.output = lambda msg: stdout.write(msg+'\n')
    
    def __format(self, msg):
        """ msg is dbus.lowlevel.Message
        args_list auto_start destination error_name interface member no_reply
        path reply_serial sender serial signature type
        """
        m = MessageFieldsGetter(msg)
        
        sender = m.sender
        if sender and sender[0] == ':' and sender in self.services:
            sender = self.services[sender]
        
        destination = m.destination
        if destination and destination[0] == ':' and destination in self.services:
            destination = self.services[destination]
        
        actors = ''
        if m.type == TYPE_SIGNAL:
            actors = 'SIGNAL %s' % sender
        elif m.type in [TYPE_CALL, TYPE_RETURN]:
            actors = 'CALL %s -> %s' % (sender, destination)
        elif m.type == TYPE_ERROR:
            actors = 'ERROR %s' % m.error_name
        
        args = ', '.join(map(str, m.args_list))
        return '%s %s(%s)' % (actors, m.member, args)
    
    def __call__(self, abus, msg):
        try:
            message = '[DBUS] %s' % self.__format(msg)
            self.output(message)
        # exceptions in signal handlers are eaten by the bindings,
        # so we better do something ourselves
        # http://bugs.freedesktop.org/show_bug.cgi?id=9980
        except:
            import traceback
            traceback.print_exc()


def monitor(output='syslog'):
    bus = SystemBus()
    logger = DBusLogger(output)
    
    bus.add_match_string("")
    bus.add_message_filter(logger)
    
    loop = MainLoop()
    print "Press Ctrl-C to stop."
    try:
        loop.run()
    except:
        print " Loop exited"
    
    bus.remove_message_filter(logger)
    bus.remove_match_string("")
