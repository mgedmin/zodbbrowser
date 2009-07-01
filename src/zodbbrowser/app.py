"""
zodbbrowser application
"""

import inspect
import pdb
import time
from cgi import escape

from BTrees._OOBTree import OOBTree
from BTrees.Length import Length

from ZODB.utils import u64
from persistent import Persistent
from zope.traversing.interfaces import IContainmentRoot
from zope.proxy import removeAllProxies
from zope.component import adapts
from zope.interface import implements
from zope.interface import Interface

from ZODB.DB import Connection
from ZODB.FileStorage import FileStorage


class IValueRenderer(Interface):

    def render(self):
        """Render object value to HTML."""


class ZodbObjectAttribute(object):

    def __init__(self, name, value, tid=None):
        self.name = name
        self.value = value
        self.tid = tid

    def rendered_name(self):
        return IValueRenderer(self.name).render()

    def rendered_value(self):
        if isinstance(self.value, Persistent):
            return PersistentValue(self.value, self.tid).render()
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
#    adapts(Persistent)
    implements(IValueRenderer)

    def __init__(self, context, tid):
        self.context = removeAllProxies(context)
        self.tid = tid

    def render(self):
        url = '/zodbinfo.html?oid=%d' % u64(self.context._p_oid)
        if self.tid is not None:
            url += "&tid=" + str(u64(self.tid))
        value = GenericValue(self.context).render()
        state = self.context.__getstate__()
        if isinstance(state, int):
            return '%s <strong>(value is %d)</strong>' % (value, state)
        if state is None:
            return '%s <strong>(state is None)</strong>' % (value)
        else:
            return '<a href="%s">%s</a>' % (url, value)


class IState(Interface):
    def listAttributes(self):
        pass
    def getParent(self):
        pass
    def getName(self):
        pass
    def diff(self, other):
        pass


def _diff_dicts(this, other):
        diffs = []
        for key, value in sorted(this.items()):
            if key not in other:
                diffs.append(['Added', key, value])
            elif other[key] != value:
                diffs.append(['Changed', key, value])
        for key in sorted(other):
            if key not in this:
                diffs.append(['Removed', key, value])
        return diffs


class BTreeState(object):
    adapts(tuple)
    implements(IState)

    def __init__(self, context):
        self.btree = OOBTree()
        self.btree.__setstate__(context)

    def getName(self):
        return '???'

    def getParent(self):
        return None

    def listAttributes(self):
        return self.btree.items()

    def diff(self, other):
        if other is None:
            state = {}
        else:
            state = OOBTree()
            state.__setstate__(other)
        return _diff_dicts(self.btree, state)


class DictState(object):
    adapts(dict)
    implements(IState)

    def __init__(self, context):
        self.context = context

    def getName(self):
        return self.context['__name__']

    def getParent(self):
        if '__parent__' in self.context:
            return self.context['__parent__']
        else:
            return None

    def listAttributes(self):
        return self.context.items()

    def diff(self, other):
        if other is None:
            other = {}
        return _diff_dicts(self.context, other)


class ZodbObject(object):

    state = None
    current = True
    tid = None
    requestedTid = None

    def __init__(self, obj):
        self.obj = removeAllProxies(obj)

    def load(self, tid=None):
        """Load current state if no tid is specified"""
        self.requestedTid = tid
        history = self._gimmeHistory()
        if tid is not None:
            # load object state with tid less or equal to given tid
            self.current = False
            for i, d in enumerate(history):
                if u64(d['tid']) <= u64(tid):
                    self.tid = d['tid']
                    break
            self.current = False
        else:
            self.tid = history[0]['tid']
        loadedState = self._loadState(self.tid)
        print loadedState.__class__
        self.state = IState(loadedState)

    def getName(self):
        return self.state.getName()

    def getObjectId(self):
        return u64(self.obj._p_oid)

    def getTid(self):
        return u64(self.tid)

    def getRequestedTid(self):
        return u64(self.requestedTid)

    def getInstanceId(self):
        return str(self.obj)

    def getType(self):
        return str(getattr(self.obj, '__class__', None))

    def getPath(self):
        if IContainmentRoot.providedBy(self.obj):
            path = "/ROOT"
        else:
            parent = self.state.getParent()
            if parent is None:
                path = "/???"
            else:
                po = ZodbObject(parent)
                po.load(self.requestedTid)
                path = po.getPath() + "/" + self.state.getName()
        return path

    def listAttributes(self):
        dictionary = self.state.listAttributes()
        attrs = []
        if self.current:
            tid = None
        else:
            tid = self.tid
        for name, value in sorted(dictionary):
            attrs.append(ZodbObjectAttribute(name=name, value=value,
                         tid=self.requestedTid))
        return attrs

#    def listItems(self):
#        elems = []
#        if not hasattr(self.obj, 'items'):
#            return []
#        for key, value in sorted(self.obj.items()):
#            elems.append(ZodbObjectAttribute(name=key, value=value))
#        return elems

    def _gimmeHistory(self):
        storage = self.obj._p_jar._storage
        oid = self.obj._p_oid
        history = None
        # XXX OMG ouch
        if 'length' in inspect.getargspec(storage.history)[0]: # ZEO
            history = storage.history(oid, version='', length=999999999999)
        else: # FileStorage
            history = storage.history(oid, size=999999999999)
        return history

    def _loadState(self, tid):
        return self.obj._p_jar.oldstate(self.obj, tid)

    def listHistory(self):
        """List transactions that modified a persistent object."""
        #XXX(zv): why is this called twice?
        results = []
        if not isinstance(self.obj, Persistent):
            return results
        history = self._gimmeHistory()

        for n, d in enumerate(history):
            short = (str(time.strftime('%Y-%m-%d %H:%M:%S',
                time.localtime(d['time']))) + " "
                + d['user_name'] + " "
                + d['description'])
            # other interesting things: d['tid'], d['size']
            diff = []
            url = '/zodbinfo.html?oid=%d&tid=%d' % (u64(self.obj._p_oid),
                        u64(d['tid']))
            current = d['tid'] == self.tid
            s = self._loadState(d['tid'])
            # First state of BTrees is None
            if s is not None:
                if n < len(history) - 1:
                    diff = IState(s).diff(
                                  self._loadState(history[n + 1]['tid']))
                else:
                    diff = IState(s).diff(None)
                results.append(dict(short=short, utid=u64(d['tid']),
                        href=url, current=current,
                        diff=diff, **d))
        return results

