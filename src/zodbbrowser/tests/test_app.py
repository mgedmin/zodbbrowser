import unittest

from zope.interface import implements
from zope.traversing.interfaces import IContainmentRoot
from zope.location.interfaces import ILocation

from zodbbrowser.app import ZodbObject


class RootFolderStub(object):
    implements(IContainmentRoot)


class LocationStub(object):
    implements(ILocation)

    def __init__(self, name, parent):
        self.__name__ = name
        self.__parent__ = parent


class TestZodbObject(unittest.TestCase):

    def setUp(self):
        self.root = RootFolderStub()
        self.foo = LocationStub('foo', self.root)
        self.foobar = LocationStub('bar', self.foo)
        self.baz = LocationStub('disembodied', None)

    def test_getPath(self):
        self.assertEqual(ZodbObject(self.root).getPath(), '/')
        self.assertEqual(ZodbObject(self.foo).getPath(), '/foo/')
        self.assertEqual(ZodbObject(self.foobar).getPath(), '/foo/bar/')
        self.assertEqual(ZodbObject(self.baz).getPath(), '/???/disembodied/')


def test_suite():
    return unittest.makeSuite(TestZodbObject)
