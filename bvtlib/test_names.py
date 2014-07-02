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

from bvtlib import test_cases

class UnexpectedTrigger(Exception):
    """A test case had a trigger that we did not expect"""

ordering = [('win7x64_sp1', '64 bit Windows 7 service pack 1'),
            ('win7_sp1', '32 bit Windows 7 service pack 1'),
            ('win81', '32 bit Windows 8.1'),
            ('win8', '32 bit Windows 8'),
            ('win8x64', '64 bit Windows 8'),
            ('win81x64', '64 bit Windows 8.1'),
            ('win7', '32 bit Windows 7'),
            ('win7x64', '64 bit Windows 7'),
            ('xp', '32 bit Windows XP')]
ordermap = dict(ordering)

def make_bvt_sequence_fragment(triggers, os_name=None, guest=None,
                               done_triggers=set()):
    """Make a subsequence of tests for BVT for specific triggers"""
    seq = []
    
    for trigger in triggers:
        done_triggers.add(trigger)
        for test_case in test_cases.TEST_CASES:
            if not test_case.get('bvt'):
                continue
            if test_case['trigger'] != trigger:
                continue
            if ('operating_systems' in test_case and 
                guest not in test_case['operating_systems']):
                print os_name, 'not in supported OS set for', \
                    test_case['description']
                continue
            tc2 = dict(test_case)
            desc = test_case['description']
            tc2['description'] = desc if os_name is None else \
                desc.replace('$(OS_NAME)', os_name)
            if guest:
                tc2['guest'] = guest
            seq.append(tc2)
    return seq

def make_bvt_cases():
    """Return BVT test sequence"""
    done_triggers = set()
    seq = make_bvt_sequence_fragment(['first',
                                      'build ready',
                                      'platform install', 
                                      'platform ready', 
                                      'python ready'], 
                                     done_triggers=done_triggers)
    for guest, os_name in ordering:
        seq += make_bvt_sequence_fragment([
                'VM install', 'VM configure',
                'VM accelerate', 'VM ready'], os_name, 
                                          guest, done_triggers)
    for test_case in test_cases.TEST_CASES:
        if (test_case.get('bvt') and 
            test_case['trigger'] not in done_triggers):
            raise UnexpectedTrigger(test_case, done_triggers)
            
    return seq
