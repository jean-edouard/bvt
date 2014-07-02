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

import logging as log

from xc.bus import DBusActor, Input, Bed


class Register(DBusActor):
    """Register the device with the given synchronizer.
       URL: the url of the synchronizer (IE: autoxt1.cam.xci-test.com)
    """
    def __init__(self, args):
        DBusActor.__init__(self)
        if len(args) < 1:
            raise Exception("You should provide the URL of the synchronizer")
        self.url = args[0]
    
    def act(self):
        device = Bed.get_device_interface()
        
        if device.isRegistered():
            log.info('The device is already registered')
            return True
        
        log.debug('Setting BED registration data')
        set_data_rc, activation_id = device.set_registration_data(self.url, "")
        if set_data_rc == Bed.CERT_NEED_AUTH_CODE:
            log.debug('Authorising certificate')
            auth_rc, _ = device.register_authorize(activation_id)
            if auth_rc != 0:
                log.error('Unable to authorise certificate')
                return False
        
        input = Input.get_interface()
        self.listen_signal(input, "auth_status") # pylint: disable=E1101
        
        log.debug('Setting input context flags')
        input.auth_set_context_flags("", "", Input.AUTH_FLAG_REMOTE_USER)
        
        log.debug('Sending remote login request')
        input.auth_remote_login('admin', 'admin')
        
        log.debug('Waiting for authentication')
        wait_signal = self.wait_signal # pylint: disable=E1101
        data = wait_signal('com.citrix.xenclient.input', 'auth_status',
                           timeout=60, condition=lambda args: args[0] == 'ok')
        if data is None:
            log.error("Timeout: authentication failed")
            return False
        
        log.info("Authentication succeeded")
        return True


class Deregister(DBusActor):
    """Deregister the device from the remote synchronizer.
    """
    def __init__(self, args):
        DBusActor.__init__(self)
    
    def act(self):
        device = Bed.get_device_interface()
        
        if not device.isRegistered():
            log.info('The device is already deregistered')
            return True
        
        log.debug('deregistering...')
        device.deregister()
        
        if device.isRegistered():
            log.error('Device deregister failed')
            return False
        
        log.info('Device succesfully deregistered')
        return True
