import pdb
import transaction
from persistent import Persistent
from BTrees.OOBTree import OOBTree
from ZODB.FileStorage import FileStorage
from ZODB import DB
from zope.app.component.site import SiteManagerContainer
from zope.app.container.btree import BTreeContainer
from zope.app.container.sample import SampleContainer
from zope.app.container.interfaces import IContained
from zope.app.container.interfaces import IContainer
from zope.app.folder.interfaces import IFolder
from zope.app.folder import Folder
from zope.app.interface import Interface
from zope.component import provideAdapter
from zope.interface import implements
from zope.traversing.interfaces import IContainmentRoot
from zope.testbrowser.testing import Browser

from zope.testing import doctest

from zodbbrowser.app import _gimmeHistory
from zodbbrowser.app import ZodbObject
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


def doctest_ZodbOBject():
    """Create some ZodbObjects
    
        >>> browser = Browser()
        >>> """


def test_suite():
    suite = doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                 optionflags=doctest.ELLIPSIS
                                    | doctest.NORMALIZE_WHITESPACE
                                    | doctest.REPORT_NDIFF
                                    | doctest.REPORT_ONLY_FIRST_FAILURE)
    return suite
