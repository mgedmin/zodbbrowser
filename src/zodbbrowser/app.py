"""
zodbbrowser application
"""

import inspect
import time
from cgi import escape

from ZODB.utils import u64
from persistent import Persistent
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

    def render(self, limit=200):
        text = repr(self.context)
        if len(text) > limit:
            text = escape(text[:limit]) + '<span class="truncated">...</span>'
        else:
            text = escape(text)
        return text


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


class ListValue(object):
    adapts(list)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self):
        html = []
        for item in self.context:
            html.append(IValueRenderer(item).render())
        return '[%s]' % ', '.join(html)


class DictValue(object):
    adapts(dict)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self):
        html = []
        for key, value in sorted(self.context.items()):
            html.append(IValueRenderer(key).render() + ': ' +
                    IValueRenderer(value).render())
            return '{%s}' % ', '.join(html)


class PersistentValue(object):
    adapts(Persistent)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = removeAllProxies(context)

    def render(self):
        url = '/zodbinfo.html?oid=%d' % u64(self.context._p_oid)
        value = GenericValue(self.context).render()
        return '<a href="%s">%s</a>' % (url, value)


class ZodbObject(object):

    tid = None

    def __init__(self, obj, accessed_directly=True):
        self.accessed_directly = accessed_directly
        self.obj = removeAllProxies(obj)
        if isinstance(self.obj, Persistent):
            self.obj._p_activate()
            self.tid = self.obj._p_serial

    def getId(self):
        """Try to determine some kind of name."""
        name = unicode(getattr(self.obj, '__name__', None))
        return name

    def getInstanceId(self):
        return str(self.obj)

    def getType(self):
        return str(getattr(self.obj, '__class__', None))

    def getPath(self):
        path = ""
        o = self.obj
        while o is not None:
            if IContainmentRoot.providedBy(o):
                if path is "":
                    return "/"
                else:
                    return path
            path = "/" + ZodbObject(o).getId() + path
            o = getattr(o, '__parent__', None)
        return "/???" + path

    def listAttributes(self):
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

    def _gimmeHistory(self, storage, oid, size):
        history = None
        # XXX OMG ouch
        if 'length' in inspect.getargspec(storage.history)[0]: # ZEO
            history = storage.history(oid, version='', length=size)
        else: # FileStorage
            history = storage.history(oid, size=size)
        return history

    def _diffDict(self, old, new):
        if not hasattr(self.obj, '__dict__'):
            return []
        """Show the differences between two dicts."""
        changes = []
        for key, value in sorted(new.items()):
            if key not in old or old[key] != new[key]:
                if isinstance(new[key], dict) and isinstance(old.get(key), dict):
                    changes.append(key + ': dictionary changed:')
                    changes.append(self.diffDict(old[key], new[key]))
                else:
                    changes.append(key)
        for key in sorted(old):
            if key not in new:
                changes.append(key + ' is gone')
        return changesa

    def _loadState(self, tid):
        return self.obj._p_jar.oldstate(self.obj, tid)

    def listHistory(self, size=999999999999):
        """List transactions that modified a persistent object."""
        #XXX(zv): why is this called twice?
        results = []
        if not isinstance(self.obj, Persistent):
            return results
        storage = self.obj._p_jar._storage
        history = self._gimmeHistory(storage, self.obj._p_oid, size)

        #TODO(zv): first transacion, print all dict. Compare with previous
        # transaction
        prevtid = None
        for n, d in enumerate(history):
            short = (str(time.strftime('%Y-%m-%d %H:%M:%S',
                time.localtime(d['time']))) + " "
                + d['user_name'] + " "
                + d['description'])
            # other interesting things: d['tid'], d['size']
            diff = []
            if n == 0:
                url = '/zodbinfo.html?oid=%d' % u64(self.obj._p_oid)
            else:
                url = '/zodbinfo.html?oid=%d&tid=%d' % (u64(self.obj._p_oid),
                        u64(d['tid']))
                current = d['tid'] == self.tid
                # diff = self._diffDict(self._loadState(d['tid']),
                #        self._loadState(prevtid))
                prevtid = d['tid']
                results.append(dict(short=short, href=url, current=current,
                    diff=diff, **d))
        return results


class ZodbObjectState(ZodbObject):

    def __init__(self, obj, state, tid=None):
        ZodbObject.__init__(self, obj)
        self.state = state
        self.tid = tid

    def getId(self):
        name = ZodbObject.getId(self)
        if self.tid:
            name += ' (from transaction %d)' % (u64(self.tid))
        return name

    def getInstanceId(self):
        res = ZodbObject.getId(self)
        return res + ' (maybe?)'

    def getPath(self):
        res = ZodbObject.getPath(self)
        return res + ' (maybe?)'

    def listAttributes(self):
        if not isinstance(self.state, dict):
            return [ZodbObjectAttribute(name='pickled state',
                value=self.state)]
        attrs = []
        for name, value in sorted(self.state.items()):
            attrs.append(ZodbObjectAttribute(name=name, value=value))
        return attrs


