"""
zodbbrowser application
"""

import inspect
import time

from zope.security.proxy import removeSecurityProxy
from zope.traversing.interfaces import IContainmentRoot


class ZodbObject(object):

    accessed_directly = True

    def __init__(self, obj, accessed_directly=True):
        self.obj = obj
        self.accessed_directly = accessed_directly

    def getId(self):
        """Try to determine some kind of name.
        """
        return str(getattr(self.obj, '__name__', None)
               or getattr(self.obj, 'id', None)
               or getattr(self.obj, '_o_id', None))

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

