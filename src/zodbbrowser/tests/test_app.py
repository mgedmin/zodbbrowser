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
from zope.app.interface import Interface
from zope.component import provideAdapter
from zope.interface import implements
from zope.traversing.interfaces import IContainmentRoot

from zope.testing import doctest

from zodbbrowser.app import ZodbObject
from zodbbrowser.app import GenericValue, TupleValue, DictValue, ListValue, \
                            BTreeState, DictState


class RootFolderStub(SampleContainer):
    implements(IContainmentRoot)


class IPersistentStub(IContainer, IContained):
    pass


class IBTreeContainerStub(IContainer, IContained):
    pass


class PersistentStub(SampleContainer, Persistent):
    implements(IPersistentStub)

    def __init__(self):
        SampleContainer.__init__(self)


class BTreeContainerStub(BTreeContainer):
    implements(IBTreeContainerStub)

    def __init__(self):
        BTreeContainer.__init__(self)


def setUp(test):
    storage = FileStorage("test.fs")
    test.db = DB(storage)
    test.connection = test.db.open()

    provideAdapter(GenericValue)
    provideAdapter(TupleValue)
    provideAdapter(DictValue)
    provideAdapter(ListValue)
    provideAdapter(BTreeState)
    provideAdapter(DictState)

    root = RootFolderStub()
    root['item1'] = BTreeContainerStub()
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

    test.globs['dbroot'] = root
    transaction.commit()
#    pdb.set_trace()


def tearDown(test):
    test.connection.close()
    test.db.close()


def doctest_Transactions():
    """Test for transaction testing

        >>> pass

    """


def doctest_Properties():
    """Test for properties testing

        >>> o1 = ZodbObject(dbroot.data)
        >>> o1.load()
        >>> o2 = ZodbObject(dbroot['item2'])
        >>> o2.load()
        >>> o3 = ZodbObject(dbroot[u'\N{SNOWMAN}'])
        >>> o3.load()

    Test name property

        >>> o1.getName()
        '???'
        >>> o2.getName()
        u'item2'
        >>> u'\N{SNOWMAN}' == o3.getName()
        True

    """


#    def test_getPath(self):
#        self.assertEqual(ZodbObject(self.root).getPath(), ' / ROOT')
#        self.assertEqual(ZodbObject(self.foo).getPath(), ' / ROOT / foo')
#        self.assertEqual(ZodbObject(self.foobar).getPath(), ' / ROOT / foo / bar')
#        self.assertEqual(ZodbObject(self.baz).getPath(), ' / ??? / disembodied')


def test_suite():
    suite = doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                 optionflags=doctest.ELLIPSIS
                                    | doctest.NORMALIZE_WHITESPACE
                                    | doctest.REPORT_NDIFF
                                    | doctest.REPORT_ONLY_FIRST_FAILURE)
    return suite
