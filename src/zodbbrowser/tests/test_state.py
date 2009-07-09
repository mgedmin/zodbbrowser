import unittest
import sys
import tempfile
import shutil
import os

import transaction
from ZODB.FileStorage.FileStorage import FileStorage
from ZODB.DB import DB
from persistent import Persistent
from zope.app.testing import setup
from zope.app.container.sample import SampleContainer
from zope.interface.verify import verifyObject
from zope.interface import implements
from zope.component import provideAdapter
from zope.traversing.interfaces import IContainmentRoot

from zodbbrowser.interfaces import IStateInterpreter
from zodbbrowser.state import (GenericState, FallbackState)


class Frob(object):
    pass


class Root(Persistent, SampleContainer):
    implements(IContainmentRoot)


class Folder(Persistent, SampleContainer):
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


class TestGenericStateWithHistory(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp('testzodbbrowser')
        self.storage = FileStorage(os.path.join(self.tmpdir, 'Data.fs'))
        self.db = DB(self.storage)
        self.conn = self.db.open()
        self.root = self.conn.root()['root'] = Root()
        self.foo = self.root['foo'] = Folder()
        self.bar = self.root['foo']['bar'] = Folder()
        transaction.commit()
        self.foo.__name__ = 'new'
        transaction.commit()

    def tearDown(self):
        transaction.abort()
        self.conn.close()
        self.db.close()
        self.storage.close()
        shutil.rmtree(self.tmpdir)

    def test_getParent_no_tid(self):
        state = GenericState(self.bar, {'__parent__': self.foo}, None)
        self.assertEquals(state.getParent().__name__, 'new')

    def test_getParent_old_tid(self):
        self.bar._p_activate()
        tid = self.bar._p_serial
        state = GenericState(self.bar, {'__parent__': self.foo}, tid)
        self.assertEquals(state.getParent().__name__, 'foo')


class TestFallbackState(unittest.TestCase):

    def setUp(self):
        self.state = FallbackState(Frob(), object(), None)

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, self.state)

    def test_getName(self):
        self.assertEquals(self.state.getName(), '???')

    def test_getParent(self):
        self.assertEquals(self.state.getParent(), None)

    def test_listAttributes(self):
        self.assertEquals(self.state.listAttributes(),
                          [('pickled state', self.state.state)])

    def test_listItems(self):
        self.assertEquals(self.state.listItems(), None)

    def test_asDict(self):
        self.assertEquals(self.state.asDict(),
                          {'pickled state': self.state.state})


def test_suite():
    this = sys.modules[__name__]
    return unittest.defaultTestLoader.loadTestsFromModule(this)

