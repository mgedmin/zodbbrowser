import time
from cgi import escape

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.publication.zopepublication import ZopePublication
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.component import adapts
from zope.interface import Interface
from zope.security.proxy import removeSecurityProxy
from ZODB.utils import p64, u64, tid_repr
from persistent import Persistent
from persistent.TimeStamp import TimeStamp
import simplejson

from zodbbrowser import __version__, __homepage__
from zodbbrowser.history import ZodbObjectHistory
from zodbbrowser.state import ZodbObjectState
from zodbbrowser.value import IValueRenderer
from zodbbrowser.diff import compareDictsHTML


class ZodbHelpView(BrowserView):
    """Zodb help view"""

    version = __version__
    homepage = __homepage__


class ZodbObjectAttribute(object):

    def __init__(self, name, value, tid=None):
        self.name = name
        self.value = value
        self.tid = tid

    def rendered_name(self):
        return IValueRenderer(self.name).render(self.tid)

    def rendered_value(self):
        return IValueRenderer(self.value).render(self.tid)

    def __repr__(self):
        return '%s(%r, %r, %r)' % (self.__class__.__name__, self.name,
                                   self.value, self.tid)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return (self.name, self.value, self.tid) == (other.name, other.value,
                                                     other.tid)

    def __ne__(self, other):
        return not self.__eq__(other)


class ZodbInfoView(BrowserView):
    """Zodb browser view"""

    adapts(Interface, IBrowserRequest)

    template = ViewPageTemplateFile('templates/zodbinfo.pt')

    version = __version__
    homepage = __homepage__

    def __call__(self):
        self.obj = None

        if 'oid' not in self.request:
            self.obj = self.findClosestPersistent()

        if self.obj is None:
            oid = p64(int(self.request.get('oid', self.getRootOid()), 0))
            jar = self.jar()
            self.obj = jar.get(oid)

        self.history = ZodbObjectHistory(self.obj)
        self.latest = True
        if 'tid' in self.request:
            self.state = ZodbObjectState(self.obj,
                                         p64(int(self.request['tid'], 0)))
            self.latest = False
        else:
            self.state = ZodbObjectState(self.obj)
        return self.template()

    def findClosestPersistent(self):
        obj = removeSecurityProxy(self.context)
        while not isinstance(obj, Persistent):
            try:
                obj = obj.__parent__
            except AttributeError:
                return None
        return obj

    def getRequestedTid(self):
        if 'tid' in self.request:
            return self.request['tid']
        else:
            return None

    def getRequestedTidNice(self):
        if 'tid' in self.request:
            return self._tidToTimestamp(p64(int(self.request['tid'], 0)))
        else:
            return None

    def getObjectId(self):
        return self.state.getObjectId()

    def getObjectType(self):
        return str(getattr(self.obj, '__class__', None))

    def getStateTid(self):
        return u64(self.state.tid)

    def getStateTidNice(self):
        return self._tidToTimestamp(self.state.tid)

    def getRootOid(self):
        root = self.jar().root()
        try:
            root = root[ZopePublication.root_name]
        except KeyError:
            pass
        return u64(root._p_oid)

    def locate_json(self, path):
        return simplejson.dumps(self.locate(path))

    def jar(self):
        try:
            return self.request.annotations['ZODB.interfaces.IConnection']
        except KeyError:
            obj = removeSecurityProxy(self.context)
            while not isinstance(obj, Persistent):
                obj = removeSecurityProxy(obj.__parent__)
            return obj._p_jar

    def locate(self, path):
        jar = self.jar()
        oid = self.getRootOid()
        partial = here = '/'
        obj = jar.get(p64(oid))
        not_found = object()
        for step in path.split('/'):
            if not step:
                continue
            if here != '/':
                here += '/'
            here += step.encode('utf-8')
            try:
                child = obj[step]
            except Exception:
                child = getattr(obj, step, not_found)
                if child is not_found:
                    return dict(error='Not found: %s' % here,
                                partial_oid=oid,
                                partial_path=partial,
                                partial_url=self.getUrl(oid))
            obj = child
            if isinstance(obj, Persistent):
                partial = here
                oid = u64(obj._p_oid)
        if not isinstance(obj, Persistent):
            return dict(error='Not persistent: %s' % here,
                        partial_oid=oid,
                        partial_path=partial,
                        partial_url=self.getUrl(oid))
        return dict(oid=oid,
                    url=self.getUrl(oid))

    def getUrl(self, oid=None, tid=None):
        url = "@@zodbbrowser?oid="
        if oid is not None:
            url += str(oid)
        else:
            url += str(self.getObjectId())

        if tid is None and 'tid' in self.request:
            url += "&tid=" + self.request['tid']
        elif tid is not None:
            url += "&tid=" + str(tid)
        return url

    def getBreadcrumbs(self):
        breadcrumbs = []
        state = self.state
        seen_root = False
        while True:
            url = self.getUrl(state.getObjectId())
            if state.isRoot():
                breadcrumbs.append(('/', url))
                seen_root = True
            else:
                if breadcrumbs:
                    breadcrumbs.append(('/', None))
                breadcrumbs.append((state.getName() or '???', url))
            state = state.getParentState()
            if state is None:
                if not seen_root:
                    url = self.getUrl(self.getRootOid())
                    breadcrumbs.append(('/', None))
                    breadcrumbs.append(('...', None))
                    breadcrumbs.append(('/', url))
                break
        return breadcrumbs[::-1]

    def getPath(self):
        return ''.join(name for name, url in self.getBreadcrumbs())

    def getBreadcrumbsHTML(self):
        html = []
        for name, url in self.getBreadcrumbs():
            if url:
                html.append('<a href="%s">%s</a>' % (escape(url, True),
                                                     escape(name)))
            else:
                html.append(escape(name))
        return ''.join(html)

    def listAttributes(self):
        attrs = self.state.listAttributes()
        if attrs is None:
            return None
        return [ZodbObjectAttribute(name, value, self.state.requestedTid)
                for name, value in sorted(attrs)]

    def listItems(self):
        items = self.state.listItems()
        if items is None:
            return None
        return [ZodbObjectAttribute(name, value, self.state.requestedTid)
                for name, value in items]

    def listHistory(self):
        """List transactions that modified a persistent object."""
        results = []

        for n, d in enumerate(self.history.history):
            short = (str(time.strftime('%Y-%m-%d %H:%M:%S',
                                       time.localtime(d['time']))) + " "
                     + d['user_name'] + " "
                     + d['description'])
            url = self.getUrl(tid=u64(d['tid']))
            current = d['tid'] == self.state.tid and \
                                  self.state.requestedTid is not None
            curState = ZodbObjectState(self.obj, d['tid']).asDict()
            if n < len(self.history) - 1:
                oldState = ZodbObjectState(self.obj, self.history[n + 1]['tid']).asDict()
            else:
                oldState = {}
            diff = compareDictsHTML(curState, oldState, d['tid'])

            results.append(dict(short=short, utid=u64(d['tid']),
                                href=url, current=current, diff=diff, **d))

        for i in range(len(results)):
            results[i]['index'] = len(results) - i

        return results

    def _tidToTimestamp(self, tid):
        if isinstance(tid, str) and len(tid) == 8:
            return str(TimeStamp(tid))
        return tid_repr(tid)
