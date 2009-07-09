"""
zodbbrowser application
"""

import time

from ZODB.utils import u64
from persistent import Persistent
from zope.traversing.interfaces import IContainmentRoot
from zope.proxy import removeAllProxies
from zope.component import getMultiAdapter

from zodbbrowser.interfaces import IValueRenderer, IStateInterpreter
from zodbbrowser.history import getHistory


class ZodbObjectAttribute(object):

    def __init__(self, name, value, tid=None):
        self.name = name
        self.value = value
        self.tid = tid

    def rendered_name(self):
        return IValueRenderer(self.name).render(self.tid)

    def rendered_value(self):
        return IValueRenderer(self.value).render(self.tid)


class ZodbObject(object):

    state = None
    current = True
    tid = None
    requestedTid = None
    history = None

    def __init__(self, obj):
        self.obj = removeAllProxies(obj)

    def load(self, tid=None):
        """Load current state if no tid is specified"""
        self.requestedTid = tid
        self.history = getHistory(self.obj)
        if tid is not None:
            # load object state with tid less or equal to given tid
            self.current = False
            for i, d in enumerate(self.history):
                if u64(d['tid']) <= u64(tid):
                    self.tid = d['tid']
                    break
            self.current = False
        else:
            self.tid = self.history[0]['tid']
        self.state = self._loadState(self.tid)

    def listAttributes(self):
        attrs = self.state.listAttributes()
        if attrs is None:
            return None
        return [ZodbObjectAttribute(name, value, self.requestedTid)
                for name, value in sorted(attrs)]

    def listItems(self):
        items = self.state.listItems()
        if items is None:
            return None
        return [ZodbObjectAttribute(name, value, self.requestedTid)
                for name, value in items]

    def _loadState(self, tid):
        loadedState = self.obj._p_jar.oldstate(self.obj, tid)
        return getMultiAdapter((self.obj, loadedState, self.requestedTid),
                               IStateInterpreter)

    def getName(self):
        if self.isRoot():
            return "ROOT"
        else:
            return self.state.getName()

    def getObjectId(self):
        return u64(self.obj._p_oid)

    def getParent(self):
        return self.state.getParent()

    def isRoot(self):
        if IContainmentRoot.providedBy(self.obj):
            return True
        else:
            return False

    def listHistory(self):
        """List transactions that modified a persistent object."""
        results = []
        if not isinstance(self.obj, Persistent):
            return results

        for n, d in enumerate(self.history):
            short = (str(time.strftime('%Y-%m-%d %H:%M:%S',
                                       time.localtime(d['time']))) + " "
                     + d['user_name'] + " "
                     + d['description'])
            url = '@@zodbbrowser?oid=%d&tid=%d' % (u64(self.obj._p_oid),
                                                   u64(d['tid']))
            current = d['tid'] == self.tid and self.requestedTid is not None
            curState = self._loadState(d['tid']).asDict()
            if n < len(self.history) - 1:
                oldState = self._loadState(self.history[n + 1]['tid']).asDict()
            else:
                oldState = {}
            diff = _diff_dicts(curState, oldState)
            for key, (action, value) in diff.items():
                diff[key][1] = IValueRenderer(value).render(d['tid'])

            results.append(dict(short=short, utid=u64(d['tid']),
                                href=url, current=current, diff=diff, **d))

        for i in range(len(results)):
            results[i]['index'] = len(results) - i

        return results


def _diff_dicts(this, other):
    diffs = {}
    for key, value in sorted(this.items()):
        if key not in other:
            diffs[key] = ['added', value]
        elif other[key] != value:
            diffs[key] = ['changed to', value]
    for key, value in sorted(other.items()):
        if key not in this:
            diffs[key] = ['removed', value]
    return diffs

