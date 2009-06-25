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
        # TODO(zv): pass tid to here
        url = '/zodbinfo.html?oid=%d' % u64(self.context._p_oid)
        value = GenericValue(self.context).render()
        return '<a href="%s">%s</a>' % (url, value)


class ZodbObject(object):

    def __init__(self, obj, tid=None):
        self.obj = removeAllProxies(obj)
        if tid is None:
            self.current = True
            self.tid = self.obj._p_serial
            if hasattr(self.obj, '__dict__'):
                self.state = self.obj.__dict__
            else:
                self.state = {}
        else:
            self.tid = tid
            self.current = False
            # load object state with tid less or equal to given tid
            self.state = self.obj._p_jar.oldstate(self.obj, tid)
        self.requestTid = tid

    def getId(self):
        """Try to determine some kind of name."""
        name = unicode(getattr(self.obj, '__name__', None))
        return name

    def getTid(self):
        return u64(self.tid)

    def getInstanceId(self):
        instanceId = str(self.obj)
        return instanceId

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
            if not self.current:
                path = "/" + ZodbObject(o, self.requestTid).getId() + path
            else:
                path = "/" + ZodbObject(o).getId() + path
            o = getattr(o, '__parent__', None)
        return "/???" + path

    def listAttributes(self):
        attrs = []

        for name, value in sorted(self.state.items()):
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
        """Show the differences between two dicts."""
        diffs = []
        for key, value in sorted(new.items()):
            if key not in old:
                diffs.append(['Added', key, value])
            elif old[key] != value:
                diffs.append(['Changed', key, value])
        for key in sorted(old):
            if key not in new:
                diffs.append(['Removed', key, value])
        return diffs

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
            if n < len(history) - 1:
                diff = self._diffDict(self._loadState(history[n + 1]['tid']),
                        self._loadState(d['tid']))
            else:
                diff = self._diffDict({}, self._loadState(d['tid']))
            results.append(dict(short=short, href=url, current=current,
                diff=diff, **d))
        return results

