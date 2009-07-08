import transaction
from BTrees.OOBTree import OOBTree
from ZODB.FileStorage import FileStorage
from ZODB import DB
from zope.app.container.btree import BTreeContainer
from zope.component import provideAdapter
from zope.interface import implements
from zope.testbrowser.testing import Browser
from zope.traversing.interfaces import IContainmentRoot

from zope.testing import doctest

from zodbbrowser.app import GenericValue, TupleValue, DictValue, ListValue, \
                            PersistentValue, OOBTreeState, GenericState


class RootFolderStub(BTreeContainer):
    implements(IContainmentRoot)


class PersistentStub(BTreeContainer):
    pass


def setUp(test):
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
    root.data = sampleTree

    test.connection.root()['test_app'] = root
    transaction.commit()

    test.globs['dbroot'] = root


def tearDown(test):
    test.connection.close()
    test.db.close()


def doctest_ZodbOBject():
    """Create some ZodbObjects

        >>> browser = Browser()

    """


def test_suite():
    suite = doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                 optionflags=doctest.ELLIPSIS
                                    | doctest.NORMALIZE_WHITESPACE
                                    | doctest.REPORT_NDIFF
                                    | doctest.REPORT_ONLY_FIRST_FAILURE)
    return suite
