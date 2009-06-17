"""
zodbbrowser application
"""

import ZODB, ZODB.FileStorage

from persistent import Persistent
from zope.interface import implements
from zope.app.container.sample import SampleContainer
from zope.security.proxy import removeSecurityProxy

from zodbbrowser.interfaces import IZodbBrowser
from zodbbrowser.interfaces import IContent


class ZodbObject(object):

    def __init__(self, obj):
        self.obj = obj

    def getId(self):
        """Try to determine some kind of name.
        """
        return (getattr(self.obj, '__name__', None)
               or getattr(self.obj, 'id', None)
               or getattr(self.obj, '_o_id', None))

    def getInstanceId(self):
        return str(self.obj)

    def getType(self):
        return str(getattr(self.obj, '__class__', None))

    def children(self):
        return []

    def getMappingItems(self):
        """Get the elements of a mapping.

        The elements are delivered as a list of dicts, each dict
        containing the keys ``key``, ``key_string`` (the key as a
        string), ``value``, ``value_type`` and ``value_type_link``.
        """
        elems = []
        naked = removeSecurityProxy(self.obj)
        if not hasattr(naked, 'items'):
            return []
        for key, value in naked.items():
            # print str(value)
            elems.append(ZodbObject(value))
        return elems

    id = property(getId)
    instanceId = property(getInstanceId)
    type = property(getType)
    children = property(getMappingItems)


class ZodbBrowser(Persistent, SampleContainer):
    """ZODB browser"""

    implements(IZodbBrowser)
    __parent__ = None

    def __init__(self):
        SampleContainer.__init__(self)
        self['content1'] = Content()
        self['content2'] = Content()


class Content(Persistent):
    """Dummy object for container testing"""

    implements(IContent)

    __parent__ = None
    __name__ = "container"

    pass

