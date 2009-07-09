import unittest
import sys

from zope.app.testing import setup
from zope.interface.verify import verifyObject
from zope.component import provideAdapter

from zodbbrowser.interfaces import IStateInterpreter
from zodbbrowser.state import (GenericState)


class Frob(object):
    pass


class TestGenericState(unittest.TestCase):

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, GenericState(Frob(), {}, None))

    def test_getName_no_name(self):
        self.assertEquals(GenericState(Frob(), {}, None).getName(), '???')

    def test_getName_with_name(self):
        state = GenericState(Frob(), {'__name__': 'xyzzy'}, None)
        self.assertEquals(state.getName(), 'xyzzy')

    def test_getParent_no_parent(self):
        self.assertEquals(GenericState(Frob(), {}, None).getParent(), None)

    def test_getParent_with_parent(self):
        parent = Frob()
        state = GenericState(Frob(), {'__parent__': parent}, None)
        self.assertEquals(state.getParent(), parent)

    # XXX: test getParent with tid loads old state of parent.

    def test_listAttributes(self):
        state = GenericState(Frob(), {'foo': 1, 'bar': 2, 'baz': 3}, None)
        self.assertEquals(sorted(state.listAttributes()),
                          [('bar', 2), ('baz', 3), ('foo', 1)])

    def test_listItems(self):
        state = GenericState(Frob(), {'foo': 1, 'bar': 2, 'baz': 3}, None)
        self.assertEquals(state.listItems(), None)

    def test_asDict(self):
        state = GenericState(Frob(), {'foo': 1, 'bar': 2, 'baz': 3}, None)
        self.assertEquals(state.asDict(), {'foo': 1, 'bar': 2, 'baz': 3})


def test_suite():
    this = sys.modules[__name__]
    return unittest.defaultTestLoader.loadTestsFromModule(this)

