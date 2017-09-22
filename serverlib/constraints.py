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

import StringIO
from funcparserlib.parser import some, a, many
from serverlib import tags

class Token(object):
    def __init__(self, code, value):
        self.code = code
        self.value = value

    @property
    def type(self):
        return self.code

    def __unicode__(self):
        return repr(self.value)

    def __repr__(self):
        return 'Token(%r, %r)' % (
            self.code, self.value)

    def __eq__(self, other):
        return (self.code, self.value) == (other.code, other.value)


def tokenize(text):
    """The world's naffest lexer"""
    seq = []
    for ch in text:
        seq.append( Token('OP' if ch in '/=' else 'CHAR', ch))
    return seq + [Token( 'END', '')]
    
def possible_int(string):
    """Make into an integer if possible"""
    try:
        return int(string)
    except ValueError:
        return string

# pylint: disable=R0914
def parse(constraints): 
    """Using funcparserlib turn constraints into a mongo query

    NOTE: this uses functors, see:

    http://spb-archlinux.ru/2009/funcparserlib/Tutorial
    """
    tokval = lambda tok: tok.value
    char = lambda tok: tok.code == 'CHAR'
    chars = some( char )>>tokval
    operator = lambda s: a(Token('OP',s)) >> tokval
    const = lambda x : lambda _: x
    makeop = lambda s: operator(s) >> const(s)
    
    item = many (chars) >> (
        lambda x: ''.join(x))
    test1 = item.parse(tokenize('hello123'))
    assert test1 == 'hello123'
    test1b = item.parse(tokenize('42a'))
    assert test1b == '42a'
    test1c = item.parse(tokenize('cam-oeprod-123299-master'))
    assert test1c == 'cam-oeprod-123299-master'
    test1d = item.parse(tokenize('Hello world'))
    assert test1d == 'Hello world'
    equals = makeop('=')
    assert  equals.parse(tokenize('=')) == '='
    slash = makeop('/')
    value = item >> possible_int
    term = (item + equals + value) >> (lambda x: (x[0], x[2]))
    test2 = term.parse(tokenize('dut=catgut'))
    assert test2 == ('dut','catgut')
    endmark = a(Token('END', ''))
    seq = (many( ((slash + term) >> (lambda x: x[1])) ) >> dict)
    top = (seq + endmark) >> (lambda x: x[0])
    test3 = seq.parse(tokenize(
            '/dut=catgut/foo=bar/n=30/bet=a42a/message=Hello World'))
    assert test3 == {'dut': 'catgut', 'foo': 'bar', 'n': 30, 
                     'message':'Hello World', 'bet': 'a42a'}
    test4 = seq.parse(tokenize('/suppress=,bar'))
    assert test4 == {'suppress': ',bar'}
    lexemes = tokenize(constraints)
    return top.parse(lexemes)

def unparse(query):
    """Turn a parse dictionry back into a string"""
    return ''.join( '/%s=%s' % (k, str(v)) for k, v in sorted(query.items()))

def cross_reference(base, query):
    """Build a cross reference taking into acount offset/limit change"""
    return lambda o, n: base+unparse(dict(query, offset=o, limit=n))

def lookup(base, oquery, key, altkey=None):
    """produce a link to a filtered version of a page"""
    if altkey is None:
        altkey = key
    def render(rec):
        """produce HTML"""
        if rec.get(key) is None:
            return '(unknown)'
        nquery = dict(oquery)
        nquery[key] = rec[key]
        return tags.a(href = base + unparse(nquery))[rec.get(altkey, rec[key])]
    return (key, render)
