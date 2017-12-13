import unittest
import sys

import transaction
from BTrees.Length import Length
from persistent import Persistent
from persistent.dict import PersistentDict
from zope.app.container.ordered import OrderedContainer
from zope.app.container.sample import SampleContainer
from zope.app.testing import setup
from zope.component import provideAdapter
from zope.container.contained import ContainedProxy
from zope.interface import implementer, alsoProvides, Interface
from zope.interface.interface import InterfaceClass
from zope.interface.verify import verifyObject
from zope.traversing.interfaces import IContainmentRoot

from zodbbrowser.interfaces import IStateInterpreter
from zodbbrowser.history import ZodbObjectHistory
from zodbbrowser.state import (
    ZodbObjectState,
    LoadErrorState,
    GenericState,
    PersistentDictState,
    PersistentMappingState,
    SampleContainerState,
    OrderedContainerState,
    ContainedProxyState,
    FallbackState,
    install_provides_hack,
    uninstall_provides_hack,
    flatten_interfaces,
)
from zodbbrowser.tests.realdb import RealDatabaseTest


class Frob(object):
    pass


@implementer(IContainmentRoot)
class Root(Persistent, SampleContainer):
    pass


class SampleFolder(Persistent, SampleContainer):

    def _newContainerData(self):
        return PersistentDict()


class PersistentObject(Persistent):
    pass # we need a subclass so we get a __dict__


class NamedSampleFolder(SampleFolder):
    __name__ = 'sample_folder'


class SeriouslyBrokenName(Persistent):

    @property
    def __name__(self):
        raise Exception('nobody expects this!')


class IMyInterface(Interface):
    __module__ = 'zodbbrowser.nosuchmodule'


class IMyGoodInterface(Interface):
    pass


class NotAnInterface(object):
    """A stand in for a ZODB Broken object"""
    __module__ = 'zodbbrowser.nosuchmodule'
    __name__ = 'NotAnInterface'


FixedNotAnInterface = InterfaceClass(
    'NotAnInterface', __module__='broken zodbbrowser.nosuchmodule')


class CrashOnUnpickling(object):

    def __getstate__(self):
        return {}

    def __setstate__(self, state):
        raise Exception('oops')


class TestFlattenInterfaces(unittest.TestCase):

    def test(self):
        self.assertEqual(
            flatten_interfaces([
                IMyGoodInterface,
                NotAnInterface,
                (NotAnInterface, IMyGoodInterface)
            ]),
            [
                IMyGoodInterface,
                FixedNotAnInterface,
                FixedNotAnInterface,
                IMyGoodInterface,
            ]
        )


class TestBrokenIntefaces(RealDatabaseTest):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(GenericState)
        RealDatabaseTest.setUp(self)
        self.obj = self.conn.root()['obj'] = SampleFolder()
        alsoProvides(self.obj, IMyInterface, IMyGoodInterface)
        sys.modules['zodbbrowser.nosuchmodule'] = sys.modules[__name__]
        transaction.commit()
        sys.modules.pop('zodbbrowser.nosuchmodule', None)
        install_provides_hack()

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()
        sys.modules.pop('zodbbrowser.nosuchmodule', None)
        uninstall_provides_hack()

    def test(self):
        state = ZodbObjectState(self.obj)
        self.assertEqual(state.getError(), None)


class TestZodbObjectState(RealDatabaseTest):

    if not hasattr(unittest.TestCase, 'assertRegex'):
        assertRegex = unittest.TestCase.assertRegexpMatches

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(GenericState)
        provideAdapter(ZodbObjectHistory)
        RealDatabaseTest.setUp(self)
        self.obj = self.conn.root()['obj'] = SampleFolder()
        self.named_obj = self.conn.root()['named_obj'] = NamedSampleFolder()
        self.root = self.conn.root()['application'] = Root()
        self.child = self.root['child'] = SampleFolder()
        transaction.commit()

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    def testZodbObjectState(self):
        state = ZodbObjectState(self.obj)
        self.assertEqual(state.getError(), None)
        self.assertEqual(state.listItems(), None)
        self.assertEqual(list(state.listAttributes())[0][0],
                         '_SampleContainer__data')
        self.assertEqual(state.getParent(), None)
        self.assertEqual(state.getParentState(), None)
        self.assertEqual(state.getName(), None)
        self.assertTrue('_SampleContainer__data' in state.asDict().keys())

    def testNameFromClassAttribute(self):
        state = ZodbObjectState(self.named_obj)
        self.assertEqual(state.getName(), 'sample_folder')

    def testRootFolder(self):
        self.assertTrue(ZodbObjectState(self.root).isRoot())
        self.assertFalse(ZodbObjectState(self.obj).isRoot())

    def testParentState(self):
        state = ZodbObjectState(self.child).getParentState()
        self.assertTrue(state.isRoot())

    def testNameResiliency(self):
        obj = self.conn.root()['obj'] = SeriouslyBrokenName()
        transaction.commit()
        state = ZodbObjectState(obj)
        self.assertEqual(state.getName(), None)

    def testUnpickleErrorHandling(self):
        obj = self.conn.root()['obj'] = PersistentObject()
        obj.attribute = CrashOnUnpickling()
        transaction.commit()
        state = ZodbObjectState(obj)
        self.assertEqual(state.getError(), 'Exception: oops')

    def testAdapterLookupErrorHandling(self):
        obj = self.conn.root()['obj'] = Length()
        transaction.commit()
        state = ZodbObjectState(obj)
        self.assertRegex(state.getError(), '^ComponentLookupError: ')


class TestLoadErrorState(unittest.TestCase):

    def setUp(self):
        self.state = LoadErrorState("Failed: because", None)

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, self.state)

    def test_getError(self):
        self.assertEqual(self.state.getError(), "Failed: because")

    def test_getName(self):
        self.assertEqual(self.state.getName(), None)

    def test_getParent(self):
        self.assertEqual(self.state.getParent(), None)

    def test_listAttributes(self):
        self.assertEqual(self.state.listAttributes(), [])

    def test_listItems(self):
        self.assertEqual(self.state.listItems(), None)

    def test_asDict(self):
        self.assertEqual(self.state.asDict(), {})


class TestGenericState(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(ZodbObjectHistory)

    def tearDown(self):
        setup.placelessTearDown()

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, GenericState(Frob(), {}, None))

    def test_getError(self):
        self.assertEqual(GenericState(Frob(), {}, None).getError(), None)

    def test_getName_no_name(self):
        self.assertEqual(GenericState(Frob(), {}, None).getName(), None)

    def test_getName_with_name(self):
        state = GenericState(Frob(), {'__name__': 'xyzzy'}, None)
        self.assertEqual(state.getName(), 'xyzzy')

    def test_getParent_no_parent(self):
        self.assertEqual(GenericState(Frob(), {}, None).getParent(), None)

    def test_getParent_with_parent(self):
        parent = Frob()
        state = GenericState(Frob(), {'__parent__': parent}, None)
        self.assertEqual(state.getParent(), parent)

    def test_listAttributes(self):
        state = GenericState(Frob(), {'foo': 1, 'bar': 2, 'baz': 3}, None)
        self.assertEqual(sorted(state.listAttributes()),
                         [('bar', 2), ('baz', 3), ('foo', 1)])

    def test_listItems(self):
        state = GenericState(Frob(), {'foo': 1, 'bar': 2, 'baz': 3}, None)
        self.assertEqual(state.listItems(), None)

    def test_asDict(self):
        state = GenericState(Frob(), {'foo': 1, 'bar': 2, 'baz': 3}, None)
        self.assertEqual(state.asDict(), {'foo': 1, 'bar': 2, 'baz': 3})


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
        self.assertEqual(state.getParent().__name__, 'new')

    def test_getParent_old_tid(self):
        self.bar._p_activate()
        tid = self.bar._p_serial
        state = GenericState(self.bar, {'__parent__': self.foo}, tid)
        # previously we mistakenly thought we ought to rewind the parent
        # object to the old state, but that's (a) unnecessary --
        # ZodbObjectState.getParentState() takes care of that -- and (b)
        # very very dangerous: https://launchpad.net/zodbbrowser/+bug/487243
        self.assertEqual(state.getParent().__name__, 'new')


class TestPersistentDictSate(unittest.TestCase):

    def test_listItems(self):
        state = PersistentDictState(Frob(),
                                    {'data': dict(a=42, b=23, c=17)},
                                    None)
        self.assertEqual(state.listItems(),
                         [('a', 42), ('b', 23), ('c', 17)])

    def test_listItems_no_data(self):
        # shouldn't happen, but let's display what exists in the DB instead
        # of crashing
        state = PersistentDictState(Frob(), {}, None)
        self.assertEqual(state.listItems(), [])


class TestPersistentMappingSate(unittest.TestCase):

    def test_listItems(self):
        state = PersistentMappingState(Frob(),
                                       {'data': dict(a=42, b=23, c=17)},
                                       None)
        self.assertEqual(state.listItems(),
                         [('a', 42), ('b', 23), ('c', 17)])

    def test_listItems_no_data(self):
        # shouldn't happen, but let's display what exists in the DB instead
        # of crashing
        state = PersistentMappingState(Frob(), {}, None)
        self.assertEqual(state.listItems(), [])


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
        self.assertEqual(list(self.state.listItems()),
                         [('bar', 2), ('foo', 1)])

    def test_listItems_no_data(self):
        state = SampleContainerState(None, SampleFolder().__getstate__(),
                                     None)
        self.assertEqual(list(state.listItems()), [])


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
        self.assertEqual(list(self.state.listItems()),
                         [('foo', 1), ('bar', 2)])

    def test_listItems_does_not_change_persistent_objects(self):
        self.container['baz'] = 3
        transaction.commit()
        # State still shows old history
        self.assertEqual(list(self.state.listItems()),
                         [('foo', 1), ('bar', 2)])
        # This doesn't affect any real objects:
        self.assertEqual(list(self.container.items()),
                         [('foo', 1), ('bar', 2), ('baz', 3)])

    def test_listItems_nonpersistent_order(self):
        # I once saw a live OrderedContainer that had a plain mutable
        # builtin list in its _order attribute
        self.container._order = list(self.container._order)
        transaction.commit()
        self.tid = self.container._p_serial
        self.state = OrderedContainerState(self.container,
                                           self.container.__getstate__(),
                                           self.tid)
        self.assertEqual(list(self.state.listItems()),
                         [('foo', 1), ('bar', 2)])


class TestContainedProxyState(unittest.TestCase):

    def setUp(self):
        self.parent = SampleFolder()
        self.frob = Frob()
        self.proxy = ContainedProxy(self.frob)
        self.proxy.__parent__ = self.parent
        self.proxy.__name__ = 'frob'
        self.state = ContainedProxyState(
            self.proxy, self.proxy.__getstate__(), None)

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, self.state)

    def test_getError(self):
        self.assertEqual(self.state.getError(), None)

    def test_getName(self):
        self.assertEqual(self.state.getName(), 'frob')

    def test_getParent(self):
        self.assertEqual(self.state.getParent(), self.parent)

    def test_listAttributes(self):
        self.assertEqual(
            self.state.listAttributes(),
            [
                ('__name__', 'frob'),
                ('__parent__', self.parent),
                ('proxied_object', self.frob),
            ]
        )

    def test_listItems(self):
        self.assertEqual(self.state.listItems(), [])

    def test_asDict(self):
        self.assertEqual(
            self.state.asDict(),
            {
                '__name__': 'frob',
                '__parent__': self.parent,
                'proxied_object': self.frob,
            }
        )


class TestFallbackState(unittest.TestCase):

    def setUp(self):
        self.state = FallbackState(Frob(), object(), None)

    def test_interface_compliance(self):
        verifyObject(IStateInterpreter, self.state)

    def test_getError(self):
        self.assertEqual(self.state.getError(), None)

    def test_getName(self):
        self.assertEqual(self.state.getName(), None)

    def test_getParent(self):
        self.assertEqual(self.state.getParent(), None)

    def test_listAttributes(self):
        self.assertEqual(self.state.listAttributes(),
                         [('pickled state', self.state.state)])

    def test_listItems(self):
        self.assertEqual(self.state.listItems(), None)

    def test_asDict(self):
        self.assertEqual(self.state.asDict(),
                         {'pickled state': self.state.state})

