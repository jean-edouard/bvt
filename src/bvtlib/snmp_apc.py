#!/usr/bin/python
#
# Copyright (c) 2013 Citrix Systems, Inc.
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

# modified by John Sturdy on 2013-11-07 from code at
# http://henrysmac.org/blog/2012/2/16/controlling-an-apc-pdu-from-python-via-pysnmp.html

from pysnmp.entity.rfc3413.oneliner import cmdgen  
from pysnmp.proto import rfc1902
import logging
import os
import os.path
import socket

class PduError(Exception):
    None

class PDU():
    class __PduParameters():
        def __init__(self, ipaddr, outlets=None):
            logging.basicConfig(filename=os.path.expanduser('~/pdu.log'),
                                format='%(levelname)s:%(asctime)s %(message)s',
                                level=logging.DEBUG)
            self.ip = ipaddr
            self.community = 'public' # 'private'
            self.port = 161
            self.retries = 5
            self.timeout = 1
            self.getStatusAllOutlets = (1,3,6,1,4,1,318,1,1,4,2,2,0)
            self.outletBaseOID = [1,3,6,1,4,1,318,1,1,4,4,2,1,3]
            self.setOutletStates = {'On':1,'Off':2,'Reboot':3}
            logging.info('PDU started up on '+socket.gethostname()+' with:')
            logging.info('    IP = '+self.ip)
            
    def __init__(self, ipaddr, outlets=range(1,9)): # for class PDU
        self.__pdu_params = self.__PduParameters(ipaddr, outlets)
        self.outlets = [ None for x in [ None ] + outlets ]
        print 'self.outlets is', self.outlets
        for cur_outlet_number in outlets:
            new_outlet = self.__PduOutlet(self.__pdu_params, 
                                          cur_outlet_number,
                                          self.status )
            self.outlets[cur_outlet_number] = new_outlet

    def __call__(self):
        self.print_status()
        return self.status()

    def get_outlet_by_number(self, number):
        return self.outlets[number] if (number > 0 and number < len(self.outlets)) else None

    def print_status(self):
        for i,status in enumerate(self.status()):
            outlet_number = i+1
            if os.name == 'posix':
                reset_color_string = '\033[0;0m'
                if status == 'On':  
                    color_string = '\033[1;32m'
                elif status == 'Off':
                    color_string = '\033[0;31m'
                else:
                    color_string = ''
                reset_color_string = ''
            else:
                color_string = ''
                reset_color_string = ''
            print ( color_string + str(outlet_number)+ 
                    '  ' + status + reset_color_string)

    def status(self):
        logging.info('status request')
        return self.__snmpGet__(self.__pdu_params.getStatusAllOutlets)
    
    def __snmpGet__(self,oid):
        ( errorIndication, errorStatus, 
          errorIndex, varBinds ) = cmdgen.CommandGenerator().getCmd(
            cmdgen.CommunityData('test-agent', 'public'),
            cmdgen.UdpTransportTarget((self.__pdu_params.ip,
                                       self.__pdu_params.port)),
            oid,(('SNMPv2-MIB', 'sysObjectID'), 0))
        if errorIndication:
            raise PduError(errorIndication)
        else:
            if errorStatus:
                raise PduError('%s at %s\n' % 
                               (errorStatus.prettyPrint(),
                                errorIndex and varBinds[int(errorIndex)-1] or '?'))
            else:
                for name, val in varBinds:
                    if name == oid:
                        return str(val).split()

    class __PduOutlet():
        def __init__(self, pdu_params, outlet_number, status_function):
            self.__pdu_params = pdu_params
            self.outlet_number = outlet_number
            self.__all_outlet_status_function = status_function
            
        def __call__(self,request=None):
            if request != None:
                if request:
                    self.on()
                else:
                    self.off()
            return self.status()
        
        def __snmpSet__(self,oid,val):
            errorIndication, errorStatus, \
                errorIndex, varBinds = cmdgen.CommandGenerator().setCmd(
                cmdgen.CommunityData('private', 'private', 1), 
                cmdgen.UdpTransportTarget((self.__pdu_params.ip, self.__pdu_params.port)), 
                (oid, rfc1902.Integer(str(val))))
            if errorIndication:
                raise PduError(errorIndication)
            else:
                if errorStatus:
                    raise PduError('%s at %s\n' % 
                                   (errorStatus.prettyPrint(),
                                    errorIndex and varBinds[int(errorIndex)-1] or '?'))
                else:
                    for name, val in varBinds:
                        if name == oid:
                            return str(val).split()

        def on(self):
            logging.info("ON requested for outlet # "+str(self.outlet_number))
            self.__snmpSet__(self.__pdu_params.outletBaseOID+[self.outlet_number],
                             self.__pdu_params.setOutletStates['On'])
            return self.status()
        
        def off(self):
            logging.info("OFF requested for outlet # "+str(self.outlet_number))
            self.__snmpSet__(self.__pdu_params.outletBaseOID+[self.outlet_number],
                             self.__pdu_params.setOutletStates['Off'])
            return self.status()

        def status(self):
            outlet_status = self.__all_outlet_status_function()[self.outlet_number - 1]
            if outlet_status == 'On':
                return True
            elif outlet_status == 'Off':
                return False
            raise PduError("Unrecognized PDU state error")

# for testing it:
if __name__ == '__main__':
    pattress = PDU('flipper')
    switch = pattress.get_outlet_by_number(8)
    print 'switch is', switch
    old_state = switch.status()
    print 'old state is', old_state
    if old_state:
        switch.off()
    else:
        switch.on()
    new_state = switch.status()
    print 'new state is', new_state
