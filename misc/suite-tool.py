#!/usr/bin/python

from src.bvtlib.mongodb import get_autotest
import sys
from optparse import OptionParser
from ast import literal_eval
from suites import SUITES
#
#   Need some kind of script to quickly add/modify test-suites in mongo.
#
#   Get information from user using prompt+stdin? thats for noobs
#   -num steps, commands, name 
#
#   Have user provide the mongo entry for us in JSON format.
#
#   
#
#
#


def delete_suite(mdb, options):
    #mdb.suites.remove({'name':options.delete})
    print 'Dummy func. Needs to be made safe before implementing.'

def update_suite(mdb, options):
    """Update an existing test suite using an input file. """
    f = open(options.update, 'r')
    query = literal_eval(f.readline())
    for line in f:
        mdb.suites.update(query, {'$set':literal_eval(line)})
    f.close()


def verify_entry(entry):
    """Simple sanity checking for new test suites."""
    count = 0
    if entry['name'] is None:
        return False
    if entry['steps'] is None:
        return False
    for step in range(entry['steps']):
        count+=1
        if entry['s-%s'%step] is None:
            return False
    if count != entry['steps']:
        return False
    return True

def add_new_test(mdb, options):
    f = open(options.new, 'r')
    entry = literal_eval(f.read())
    f.close()
    print entry
    if verify_entry(entry):
        mdb.suites.save(entry)
    else:
        print 'Entry format incorrect or some other error with suite entry.'
        sys.exit(-1)

def add_all(mdb, options):
    for suite in SUITES:
        mdb.suites.save(suite)

def main():
    parser = OptionParser()
    parser.add_option(
        '-n', '--new', metavar='NEW', action='store',
        help='Input file with a new suite in JSON format.')
    parser.add_option(
        '-u', '--update', metavar='UPDATE', action='store',
        help='Input file in JSON format for updating an existing test suite.')
    parser.add_option(
        '-d', '--delete', metavar='DELETE', action='store',
        help='Delete the test suite entry out of mongo. (Hypothetical implementation)')
    parser.add_option(
        '-a', '--alldb', action='store_true',
        help='Add all suites to the db in the library file.')

    options, args = parser.parse_args()
    mdb = get_autotest()

    if options.new:
        add_new_test(mdb, options)

    if options.update:
        update_suite(mdb, options)

    if options.delete:
        delete_suite(mdb, options)

    if options.alldb:
        add_all(mdb, options)






main()
