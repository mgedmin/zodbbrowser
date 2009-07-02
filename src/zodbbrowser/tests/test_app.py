import unittest
import pdb
import transaction
from persistent import Persistent
from BTrees.OOBTree import OOBTree
from ZODB.FileStorage import FileStorage
from ZODB import DB
from zope.app.container.btree import BTreeContainer
from zope.app.container.sample import SampleContainer
from zope.app.container.interfaces import IContained
from zope.app.container.interfaces import IContainer
from zope.app.container.constraints import contains
from zope.app.interface import Interface
from zope.app.folder.interfaces import IFolder
from zope.interface import implements
from zope.schema import TextLine
from zope.traversing.interfaces import IContainmentRoot
from zope.location.interfaces import ILocation

from zope.testing import doctest

from zodbbrowser.app import ZodbObject


class RootFolderStub(SampleContainer):
    implements(IContainmentRoot)


class IPersistentStub(IContainer, IContained):
    pass


class IBTreeContainerStub(IContainer, IContained):
    pass


class PersistentStub(SampleContainer, Persistent):
    implements(IPersistentStub)

    def __init__(self, name):
        SampleContainer.__init__(self)
        self.__name__ = name


class BTreeContainerStub(BTreeContainer):
    implements(IBTreeContainerStub)

    def __init__(self, name):
        BTreeContainer.__init__(self)
        self.__name__ = name


def setUp(test):
    storage = FileStorage("test.fs")
    db = DB(storage)
    test.connection = db.open()

    root = RootFolderStub()
    root['item1'] = BTreeContainerStub('item1')
    root['item2'] = PersistentStub('item2')
    root['item2']['item2.1'] = PersistentStub('item2.1')
    root['item2']['item2.2'] = PersistentStub('item2.2')

    sampleTree = OOBTree()
    sampleTree.insert('key1', 'valuex')
    sampleTree.insert('key2', 'valuey')
    sampleTree.insert('key3', 'valuez')
    root['item1']['tree'] = sampleTree
#
    test.connection.root()['test_app'] = root

    test.globs['dbroot'] = test.connection.root()['test_app']
    transaction.commit()
#    pdb.set_trace()

#        self.root = RootFolderStub()
#        self.foo = LocationStub('foo', self.root)
#        self.foobar = LocationStub('bar', self.foo)
#        self.baz = LocationStub('disembodied', None)
#        self.snowman = LocationStub(u'\N{SNOWMAN}', self.root)
#        self.unnamed = LocationStub(None, None)


def tearDown(test):
    test.connection.close()


def doctest_Transactions(test):
    """Test for transaction testing

        >>> print dbroot['item1'].__name__
        item1

    """

#    def test_getId(self):
#        self.assertEqual(ZodbObject(self.snowman).getId(), u'\N{SNOWMAN}')
#        self.assertEqual(ZodbObject(self.unnamed).getId(), u'None')

#    def test_getPath(self):
#        self.assertEqual(ZodbObject(self.root).getPath(), '/ROOT')
#        self.assertEqual(ZodbObject(self.foo).getPath(), '/ROOT/foo')
#        self.assertEqual(ZodbObject(self.foobar).getPath(), '/ROOT/foo/bar')
#        self.assertEqual(ZodbObject(self.baz).getPath(), '/???/disembodied')


def test_suite():
    suite = doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                 optionflags=doctest.ELLIPSIS
                                    | doctest.NORMALIZE_WHITESPACE
                                    | doctest.REPORT_NDIFF
                                    | doctest.REPORT_ONLY_FIRST_FAILURE)
    return suite
