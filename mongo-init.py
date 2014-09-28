#!/usr/bin/python

from src.bvtlib import mongodb

def main():

    mdb = mongodb.get_autotest()
    
    num_duts = int(input('Number of test machines to add: '))

    for i in range(num_duts):
        dut_input = {}
        dut_input['name'] = raw_input('Name of test machine: ')
        dut_input['power_control'] = raw_input('Power control type (eg. AMT): ')
        dut_input['num-nics'] = int(raw_input('Number of nics (BVT supports 1 or 2): '))
        if dut_input['num-nics'] == 2:
            dut_input['mac-net'] = raw_input('MAC address of addon NIC: ')
            bus = raw_input('PCI bus of addon NIC (default is 01):  ')
            if bus != "":
                dut_input['nic-bus'] = bus
            dut_input['mac-amt'] = raw_input('MAC address of onboard NIC: ')
        else:
            dut_input['mac'] = raw_input('MAC address of onboard NIC: ')
        dut_input['num'] = i
        dut_input['enabled'] = 1
        dut_input['acquired'] = 0
        mdb.duts.save(dut_input)
    
    num_suites = int(input('Number of test suites to add: '))
    for i in range(num_suites):
        suite_input = {}
        suite_input['name'] = raw_input('Name of test suite: ')
        suite_input['steps'] = int(raw_input('Number of steps in %s: ' % suite_input['name']))
        mdb.suites.save(suite_input)
        for j in range(suite_input['steps']):
            step = {}
            command = raw_input('Step %d Command: ' %j)
            step['s-%d'%j] = command.split()
            mdb.suites.update({'name':suite_input['name']},{'$set':step})
            
        
main()
