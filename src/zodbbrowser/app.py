"""
zodbbrowser application
"""

import inspect
import time
from cgi import escape

from ZODB.utils import u64
from persistent import Persistent
from zope.security.proxy import removeSecurityProxy
from zope.traversing.interfaces import IContainmentRoot
from zope.proxy import removeAllProxies
from zope.component import adapts
from zope.interface import implements
from zope.interface import Interface


class IValueRenderer(Interface):

    def render(self):
        """Render object value to HTML."""


class ZodbObjectAttribute(object):

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def rendered_name(self):
        return IValueRenderer(self.name).render()

    def rendered_value(self):
        return IValueRenderer(self.value).render()


class GenericValue(object):
    adapts(Interface)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self):
        return escape(repr(self.context))


class TupleValue(object):
    adapts(tuple)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render())
        if len(html) == 1:
            html.append('') # (item) -> (item, )
        return '(%s)' % ', '.join(html)


class PersistentValue(object):
    adapts(Persistent)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self):
        url = '/zodbinfo.html?oid=%d' % u64(self.context._p_oid)
        value = GenericValue(self.context).render()
        return '<a href="%s">%s</a>' % (url, value)


class ZodbObject(object):

    accessed_directly = True

    def __init__(self, obj, accessed_directly=True):
        self.obj = removeAllProxies(obj)
        self.accessed_directly = accessed_directly

    def getId(self):
        """Try to determine some kind of name."""
        return unicode(getattr(self.obj, '__name__', None))

    def getInstanceId(self):
        return str(self.obj)

    def getType(self):
        return str(getattr(self.obj, '__class__', None))

    def getPath(self):
        path = "/"
        o = self.obj
        while o is not None:
            if IContainmentRoot.providedBy(o):
                return path
            path = "/" + ZodbObject(o).getId() + path
            o = getattr(o, '__parent__', None)
        return "/???" + path

    def listAttributes(self):
        if isinstance(self.obj, Persistent):
            self.obj._p_activate()
        attrs = []
        if not hasattr(self.obj, '__dict__'):
            return attrs
        for name, value in sorted(self.obj.__dict__.items()):
            attrs.append(ZodbObjectAttribute(name=name, value=value))
        return attrs

    def listItems(self):
        elems = []
        if not hasattr(self.obj, 'items'):
            return []
        for key, value in sorted(self.obj.items()):
            elems.append(ZodbObjectAttribute(name=key, value=value))
        return elems

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
            elems.append(ZodbObject(value, False))
        return elems

    def _gimmeHistory(self, storage, oid, size):
        history = None
        # XXX OMG ouch
        if 'length' in inspect.getargspec(storage.history)[0]: # ZEO
            history = storage.history(oid, version='', length=size)
        else: # FileStorage
            history = storage.history(oid, size=size)
        return history

    def listHistory(self, size=20):
        """List transactions that modified a persistent object."""
        list = []
        naked = removeSecurityProxy(self.obj)
        storage = naked._p_jar._storage
        history = self._gimmeHistory(storage, naked._p_oid, size)
        for n, d in enumerate(history):
            list.append(str(n) + " " + str(time.strftime('%Y-%m-%d %H:%M:%S',
                time.localtime(d['time']))) + " " +  d['user_name'] + " " + d['description'])
        return list

