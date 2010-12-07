import unittest
import sys

import transaction
from persistent import Persistent
from persistent.dict import PersistentDict
from zope.app.container.ordered import OrderedContainer
from zope.app.container.sample import SampleContainer
from zope.interface.verify import verifyObject
from zope.interface import implements
from zope.traversing.interfaces import IContainmentRoot
from zope.component import provideAdapter
from zope.app.testing import setup

from zodbbrowser.interfaces import IStateInterpreter
from zodbbrowser.history import ZodbObjectHistory
from zodbbrowser.state import (ZodbObjectState,
                               GenericState,
                               PersistentDictState,
                               PersistentMappingState,
                               SampleContainerState,
                               OrderedContainerState,
                               FallbackState)
from zodbbrowser.tests.realdb import RealDatabaseTest


class Frob(object):
    pass


class Root(Persistent, SampleContainer):
    implements(IContainmentRoot)


class SampleFolder(Persistent, SampleContainer):

    def _newContainerData(self):
        return PersistentDict()


class PersistentObject(Persistent):
    pass # we need a subclass so we get a __dict__


class NamedSampleFolder(SampleFolder):
    __name__ = 'sample_folder'


class TestZodbObjectState(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(GenericState)
        provideAdapter(ZodbObjectHistory)
        RealDatabaseTest.setUp(self)
        self.obj = self.conn.root()['obj'] = SampleFolder()
        self.named_obj = self.conn.root()['named_obj'] = NamedSampleFolder()
        transaction.commit()

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    def testZodbObjectState(self):
        state = ZodbObjectState(self.obj)
        self.assertEquals(state.listItems(), None)
        self.assertTrue(state.listAttributes()[0][0], '_SampleContainer__data')
        self.assertEquals(state.getParent(), None)
        self.assertEquals(state.getName(), None)
        self.assertTrue('_SampleContainer__data' in state.asDict().keys())

    def testNameFromClassAttribute(self):
        state = ZodbObjectState(self.named_obj)
        self.assertEquals(state.getName(), 'sample_folder')


class TestGenericState(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(ZodbObjectHistory)

    def tearDown(self):
        setup.placelessTearDown()

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, GenericState(Frob(), {}, None))

    def test_getName_no_name(self):
        self.assertEquals(GenericState(Frob(), {}, None).getName(), None)

    def test_getName_with_name(self):
        state = GenericState(Frob(), {'__name__': 'xyzzy'}, None)
        self.assertEquals(state.getName(), 'xyzzy')

    def test_getParent_no_parent(self):
        self.assertEquals(GenericState(Frob(), {}, None).getParent(), None)

    def test_getParent_with_parent(self):
        parent = Frob()
        state = GenericState(Frob(), {'__parent__': parent}, None)
        self.assertEquals(state.getParent(), parent)

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


class TestGenericStateWithHistory(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(ZodbObjectHistory)
        RealDatabaseTest.setUp(self)
        self.root = self.conn.root()['root'] = Root()
        self.foo = self.root['foo'] = SampleFolder()
        self.bar = self.root['foo']['bar'] = SampleFolder()
        transaction.commit()
        self.foo.__name__ = 'new'
        transaction.commit()

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    def test_getParent_no_tid(self):
        state = GenericState(self.bar, {'__parent__': self.foo}, None)
        self.assertEquals(state.getParent().__name__, 'new')

    def test_getParent_old_tid(self):
        self.bar._p_activate()
        tid = self.bar._p_serial
        state = GenericState(self.bar, {'__parent__': self.foo}, tid)
        # previously we mistakenly thought we ought to rewind the parent
        # object to the old state, but that's (a) unnecessary --
        # ZodbObjectState.getParentState() takes care of that -- and (b)
        # very very dangerous: https://launchpad.net/zodbbrowser/+bug/487243
        self.assertEquals(state.getParent().__name__, 'new')


class TestPersistentDictSate(unittest.TestCase):

    def test_listItems(self):
        state = PersistentDictState(Frob(),
                                    {'data': dict(a=42, b=23, c=17)},
                                    None)
        self.assertEquals(state.listItems(),
                          [('a', 42), ('b', 23), ('c', 17)])

    def test_listItems_no_data(self):
        # shouldn't happen, but let's display what exists in the DB instead
        # of crashing
        state = PersistentDictState(Frob(), {}, None)
        self.assertEquals(state.listItems(), [])


class TestPersistentMappingSate(unittest.TestCase):

    def test_listItems(self):
        state = PersistentMappingState(Frob(),
                                    {'data': dict(a=42, b=23, c=17)},
                                    None)
        self.assertEquals(state.listItems(),
                          [('a', 42), ('b', 23), ('c', 17)])

    def test_listItems_no_data(self):
        # shouldn't happen, but let's display what exists in the DB instead
        # of crashing
        state = PersistentMappingState(Frob(), {}, None)
        self.assertEquals(state.listItems(), [])


class TestSampleContainerState(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(ZodbObjectHistory)
        provideAdapter(PersistentDictState)
        provideAdapter(PersistentMappingState)
        RealDatabaseTest.setUp(self)
        self.container = self.conn.root()['container'] = SampleFolder()
        self.container['foo'] = 1
        self.container['bar'] = 2
        transaction.commit()
        self.state = SampleContainerState(None, self.container.__getstate__(),
                                          None)

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    def test_listItems(self):
        self.assertEquals(list(self.state.listItems()),
                          [('bar', 2), ('foo', 1)])

    def test_listItems_no_data(self):
        state = SampleContainerState(None, SampleFolder().__getstate__(),
                                     None)
        self.assertEquals(list(state.listItems()), [])


class TestOrderedContainerState(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(ZodbObjectHistory)
        RealDatabaseTest.setUp(self)
        self.container = self.conn.root()['container'] = OrderedContainer()
        self.container['foo'] = 1
        self.container['bar'] = 2
        transaction.commit()
        self.tid = self.container._p_serial
        self.state = OrderedContainerState(self.container,
                                           self.container.__getstate__(),
                                           self.tid)

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    def test_listItems(self):
        self.assertEquals(list(self.state.listItems()),
                          [('foo', 1), ('bar', 2)])

    def test_listItems_does_not_change_persistent_objects(self):
        self.container['baz'] = 3
        transaction.commit()
        # State still shows old history
        self.assertEquals(list(self.state.listItems()),
                          [('foo', 1), ('bar', 2)])
        # This doesn't affect any real objects:
        self.assertEquals(list(self.container.items()),
                          [('foo', 1), ('bar', 2), ('baz', 3)])


class TestFallbackState(unittest.TestCase):

    def setUp(self):
        self.state = FallbackState(Frob(), object(), None)

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, self.state)

    def test_getName(self):
        self.assertEquals(self.state.getName(), None)

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

