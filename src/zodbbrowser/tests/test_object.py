import transaction
import tempfile
import shutil
import os
from BTrees.OOBTree import OOBTree
from ZODB.FileStorage import FileStorage
from ZODB import DB
from zope.app.container.btree import BTreeContainer
from zope.component import provideAdapter
from zope.interface import implements
from zope.traversing.interfaces import IContainmentRoot

from zope.testing import doctest


from zodbbrowser.object import ZodbObject
from zodbbrowser.history import getHistory
from zodbbrowser.value import (GenericValue, TupleValue, DictValue,
                               ListValue, PersistentValue)
from zodbbrowser.state import OOBTreeState, GenericState
from zodbbrowser.tests.test_diff import pprintDict


class RootFolderStub(BTreeContainer):
    implements(IContainmentRoot)


class PersistentStub(BTreeContainer):
    pass


def setUp(test):
    test.tmpdir = tempfile.mkdtemp('testzodbbrowser')
    test.storage = FileStorage(os.path.join(test.tmpdir, 'Data.fs'))
    test.db = DB(test.storage)
    test.conn = test.db.open()

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
#
    test.conn.root()['test_app'] = root
    transaction.commit()

    test.globs['dbroot'] = root


def tearDown(test):
    transaction.abort()
    test.conn.close()
    test.db.close()
    test.storage.close()
    shutil.rmtree(test.tmpdir)


def doctest_ZodbObject():
    """Create some ZodbObjects

        >>> root = ZodbObject(dbroot)
        >>> root.load()
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
        >>> o2.listAttributes()[3].rendered_name()
        "'__parent__'"
        >>> o2.listAttributes()[3].rendered_value()
        '<a href="@@zodbbrowser?oid=1">&lt;zodbbrowser.tests.test_object.RootFolderStub object at ...;</a>'
        >>> o1.listAttributes() == None
        True
        >>> o2.listItems() == None
        True

    Get parent anr root

        >>> o4.getParent()
        <zodbbrowser.tests.test_object.PersistentStub object at ...>
        >>> root.isRoot()
        True
        >>> o4.isRoot()
        False

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

        >>> history = o1.listHistory()
        >>> len(history)
        3
        >>> pprintDict(history[1])
        {'current': True,
        'description': '',
        'diff': '...key4...added...',
        'href': '@@zodbbrowser?oid=3&tid=...',
        'index': 2,
        'short': '...',
        'size': 113L,
        'tid': '...',
        'time': ...,
        'user_name': '',
        'utid': ...L,
        'version': ''}


    """


def test_suite():
    suite = doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                 optionflags=doctest.ELLIPSIS
                                    | doctest.NORMALIZE_WHITESPACE
                                    | doctest.REPORT_NDIFF
                                    | doctest.REPORT_ONLY_FIRST_FAILURE)
    return suite
