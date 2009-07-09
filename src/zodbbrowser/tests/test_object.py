import transaction
from BTrees.OOBTree import OOBTree
from ZODB.FileStorage import FileStorage
from ZODB import DB
from zope.app.container.btree import BTreeContainer
from zope.component import provideAdapter
from zope.interface import implements
from zope.traversing.interfaces import IContainmentRoot

from zope.testing import doctest


from zodbbrowser.object import ZodbObject
from zodbbrowser.value import (GenericValue, TupleValue, DictValue,
                               ListValue, PersistentValue)
from zodbbrowser.history import getHistory
from zodbbrowser.state import OOBTreeState, GenericState


class RootFolderStub(BTreeContainer):
    implements(IContainmentRoot)


class PersistentStub(BTreeContainer):
    pass


def setUp(test):
#    storage = MappingStorage("mapping")
    storage = FileStorage("test.fs")
    test.db = DB(storage)
    test.connection = test.db.open()

    provideAdapter(GenericValue)
    provideAdapter(TupleValue)
    provideAdapter(DictValue)
    provideAdapter(ListValue)
    provideAdapter(PersistentValue)
    provideAdapter(OOBTreeState)
    provideAdapter(GenericState)

    root = RootFolderStub()
    root['item1'] = PersistentStub()
    root['item2'] = PersistentStub()
    root[u'\N{SNOWMAN}'] = PersistentStub()
    root['item2']['item2.1'] = PersistentStub()
    root['item2']['item2.2'] = PersistentStub()

    sampleTree = OOBTree()
    sampleTree.insert('key1', 'valuex')
    sampleTree.insert('key2', 'valuey')
    sampleTree.insert('key3', 'valuez')
#    root['item1']['tree'] = sampleTree
    root.data = sampleTree
#
    test.connection.root()['test_app'] = root
    transaction.commit()

    test.globs['dbroot'] = root
#    pdb.set_trace()


def tearDown(test):
    test.connection.close()
    test.db.close()


def doctest_ZodbObject():
    """Create some ZodbObjects

        >>> o1 = ZodbObject(dbroot.data)
        >>> o1.load()
        >>> o2 = ZodbObject(dbroot['item2'])
        >>> o2.load()
        >>> o3 = ZodbObject(dbroot[u'\N{SNOWMAN}'])
        >>> o3.load()
        >>> o4 = ZodbObject(dbroot['item2']['item2.1'])
        >>> o4.load()

    Test name property

        >>> o1.getName()
        '???'
        >>> o2.getName()
        u'item2'
        >>> u'\N{SNOWMAN}' == o3.getName()
        True

    List attributes and items

        >>> [a.name for a in o1.listItems()]
        ['key1', 'key2', 'key3']
        >>> [a.name for a in o2.listAttributes()]
        ['_BTreeContainer__len', '_SampleContainer__data', '__name__', '__parent__']

    Test history functions

        >>> dbroot.data['key4'] = "new value"
        >>> transaction.commit()
        >>> del dbroot.data['key2']
        >>> transaction.commit()
        >>> [a.name for a in o1.listItems()]
        ['key1', 'key2', 'key3']
        >>> o1.load()
        >>> [a.name for a in o1.listItems()]
        ['key1', 'key3', 'key4']

        >>> history = getHistory(o1.obj)
        >>> len(history)
        3
        >>> o1.load(history[1]['tid'])
        >>> [a.name for a in o1.listItems()]
        ['key1', 'key2', 'key3', 'key4']

    """


def test_suite():
    suite = doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                 optionflags=doctest.ELLIPSIS
                                    | doctest.NORMALIZE_WHITESPACE
                                    | doctest.REPORT_NDIFF
                                    | doctest.REPORT_ONLY_FIRST_FAILURE)
    return suite
