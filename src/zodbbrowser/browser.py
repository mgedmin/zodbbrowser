import json
import logging
import pickletools
import time
import traceback

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.publication.zopepublication import ZopePublication, Cleanup
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.component import adapter, queryUtility
from zope.interface import Interface
from zope.security.proxy import removeSecurityProxy
from zope.cachedescriptors.property import Lazy
from zope.exceptions.interfaces import UserError
from ZODB.utils import p64, u64, tid_repr, oid_repr
from ZODB.Connection import Connection
from ZODB.interfaces import IDatabase
from ZODB.POSException import POSKeyError
from persistent import Persistent
from persistent.TimeStamp import TimeStamp
import transaction

from zodbbrowser import __version__, __homepage__
from zodbbrowser.compat import escape, StringIO, BytesIO
from zodbbrowser.diff import compareDictsHTML
from zodbbrowser.history import ZodbObjectHistory
from zodbbrowser.interfaces import IDatabaseHistory
from zodbbrowser.interfaces import IValueRenderer
from zodbbrowser.state import ZodbObjectState
from zodbbrowser.value import pruneTruncations, TRUNCATIONS


log = logging.getLogger("zodbbrowser")


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


class VeryCarefulView(BrowserView):

    made_changes = False

    @Lazy
    def jar(self):
        db = queryUtility(IDatabase, name='<target>')
        if db is not None:
            conn = db.open()
            self.request.hold(Cleanup(conn.close))
            return conn
        try:
            return self.request.annotations['ZODB.interfaces.IConnection']
        except (KeyError, AttributeError):
            obj = self.findClosestPersistent()
            if obj is None:
                raise Exception("ZODB connection not available for this request")
            return obj._p_jar

    def findClosestPersistent(self):
        obj = removeSecurityProxy(self.context)
        while not isinstance(obj, Persistent):
            try:
                obj = obj.__parent__
            except AttributeError:
                return None
        return obj

    @property
    def readonly(self):
        return self.jar.isReadOnly()

    def __call__(self):
        try:
            return self.render()
        finally:
            if self.readonly or not self.made_changes:
                resources = transaction.get()._resources
                if resources:
                    msg = ["Aborting changes made to:"]
                    for r in resources:
                        if isinstance(r, Connection):
                            for o in r._registered_objects:
                                msg.append("  oid=%s %s" % (oid_repr(o._p_oid), repr(o)))
                        else:
                            msg.append("  %s" % repr(r))
                    log.debug("\n".join(msg))
                transaction.abort()


@adapter(Interface, IBrowserRequest)
class ZodbInfoView(VeryCarefulView):
    """Zodb browser view"""

    template = ViewPageTemplateFile('templates/zodbinfo.pt')
    confirmation_template = ViewPageTemplateFile('templates/confirm_rollback.pt')

    version = __version__
    homepage = __homepage__

    def render(self):
        self._started = time.time()
        pruneTruncations()
        self.obj = self.selectObjectToView()
        # Not using IObjectHistory(self.obj) because LP#1185175
        self.history = ZodbObjectHistory(self.obj)
        self.latest = True
        if self.request.get('tid'):
            self.state = ZodbObjectState(self.obj,
                                         p64(int(self.request['tid'], 0)),
                                         _history=self.history)
            self.latest = False
        else:
            self.state = ZodbObjectState(self.obj, _history=self.history)

        if 'CANCEL' in self.request:
            self._redirectToSelf()
            return ''

        if 'ROLLBACK' in self.request:
            rtid = p64(int(self.request['rtid'], 0))
            self.requestedState = self._tidToTimestamp(rtid)
            if self.request.get('confirmed') == '1':
                self.history.rollback(rtid)
                transaction.get().note(u'Rollback to old state %s'
                                       % self.requestedState)
                self.made_changes = True
                self._redirectToSelf()
                return ''
            # will show confirmation prompt
            return self.confirmation_template()

        return self.template()

    def renderingTime(self):
        return '%.3fs |' % (time.time() - self._started)

    def _redirectToSelf(self):
        self.request.response.redirect(self.getUrl())

    def selectObjectToView(self):
        obj = None
        if 'oid' not in self.request:
            obj = self.findClosestPersistent()
            # Sanity check: if we're running in standalone mode,
            # self.context is a Folder in the just-created MappingStorage,
            # which we're not interested in.
            if obj is not None and obj._p_jar is not self.jar:
                obj = None
        if obj is None:
            if 'oid' in self.request:
                try:
                    oid = int(self.request['oid'], 0)
                except ValueError:
                    raise UserError('OID is not an integer: %r' %
                                    self.request['oid'])
            else:
                oid = self.getRootOid()
            try:
                obj = self.jar.get(p64(oid))
            except POSKeyError:
                raise UserError('There is no object with OID 0x%x' % oid)
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

    def getObjectIdHex(self):
        return '0x%x' % self.state.getObjectId()

    def getObjectType(self):
        return getObjectType(self.obj)

    def getObjectTypeShort(self):
        return getObjectTypeShort(self.obj)

    def getStateTid(self):
        return u64(self.state.tid)

    def getStateTidNice(self):
        return self._tidToTimestamp(self.state.tid)

    def getPickleSize(self):
        return len(self.state.pickledState)

    def getRootOid(self):
        root = self.jar.root()
        try:
            root = root[ZopePublication.root_name]
        except KeyError:
            pass
        return u64(root._p_oid)

    def locate_json(self, path): # AJAX view
        return json.dumps(self.locate(path))

    def truncated_ajax(self, id): # AJAX view
        return TRUNCATIONS.get(id)

    def locate(self, path):
        not_found = object() # marker

        # our current position
        #   partial -- path of the last _persistent_ object
        #   here -- path of the last object traversed
        #   oid -- oid of the last _persistent_ object
        #   obj -- last object traversed
        partial = here = '/'
        oid = self.getRootOid()
        obj = self.jar.get(p64(oid))

        steps = path.split('/')

        if steps and steps[0]:
            # 0x1234/sub/path -> start traversal at oid 0x1234
            try:
                oid = int(steps[0], 0)
            except ValueError:
                pass
            else:
                partial = here = hex(oid)
                try:
                    obj = self.jar.get(p64(oid))
                except KeyError:
                    oid = self.getRootOid()
                    return dict(error='Not found: %s' % steps[0],
                                partial_oid=oid,
                                partial_path='/',
                                partial_url=self.getUrl(oid))
                steps = steps[1:]

        for step in steps:
            if not step:
                continue
            if not here.endswith('/'):
                here += '/'
            here += step
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
        if oid is None:
            oid = self.getObjectId()
        url = "@@zodbbrowser?oid=0x%x" % oid
        if tid is None and 'tid' in self.request:
            url += "&tid=" + self.request['tid']
        elif tid is not None:
            url += "&tid=0x%x" % tid
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
                if not state.getName() and state.getParentState() is None:
                    # not using hex() because we don't want L suffixes for
                    # 64-bit values
                    breadcrumbs.append(('0x%x' % state.getObjectId(), url))
                    break
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
                                                     escape(name, False)))
            else:
                html.append(escape(name, False))
        return ''.join(html)

    def getDisassembledPickleData(self):
        pickle = BytesIO(self.state.pickledState)
        out = StringIO()
        memo = {}
        # 1st pickle: the class
        try:
            pickletools.dis(pickle, out, memo)
        except Exception as e:
            out.write(''.join(traceback.format_exception_only(type(e), e)))
        # 2st pickle: actual instance data
        out.write('\n')
        try:
            pickletools.dis(pickle, out, memo)
        except Exception as e:
            out.write(''.join(traceback.format_exception_only(type(e), e)))
        return out.getvalue()

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

    def _loadHistoricalState(self):
        results = []
        for d in self.history:
            try:
                interp = ZodbObjectState(self.obj, d['tid'],
                                         _history=self.history)
                state = interp.asDict()
                error = interp.getError()
            except Exception as e:
                state = {}
                error = '%s: %s' % (e.__class__.__name__, e)
            results.append(dict(state=state, error=error))
        results.append(dict(state={}, error=None))
        return results

    def listHistory(self):
        """List transactions that modified a persistent object."""
        state = self._loadHistoricalState()
        results = []
        for n, d in enumerate(self.history):
            utc_timestamp = str(time.strftime('%Y-%m-%d %H:%M:%S',
                                              time.gmtime(d['time'])))
            local_timestamp = str(time.strftime('%Y-%m-%d %H:%M:%S',
                                                time.localtime(d['time'])))
            try:
                user_location, user_id = d['user_name'].split()
            except ValueError:
                user_location = None
                user_id = d['user_name']
            url = self.getUrl(tid=u64(d['tid']))
            current = (d['tid'] == self.state.tid and
                       self.state.requestedTid is not None)
            curState = state[n]['state']
            oldState = state[n + 1]['state']
            diff = compareDictsHTML(curState, oldState, d['tid'])

            results.append(dict(utid=u64(d['tid']),
                                href=url, current=current,
                                error=state[n]['error'],
                                diff=diff, user_id=user_id,
                                user_location=user_location,
                                utc_timestamp=utc_timestamp,
                                local_timestamp=local_timestamp, **d))

        # number in reverse order
        for i in range(len(results)):
            results[i]['index'] = len(results) - i

        return results

    def _tidToTimestamp(self, tid):
        if isinstance(tid, bytes) and len(tid) == 8:
            return str(TimeStamp(tid))
        return tid_repr(tid)


@adapter(Interface, IBrowserRequest)
class ZodbHistoryView(VeryCarefulView):
    """Zodb history view"""

    template = ViewPageTemplateFile('templates/zodbhistory.pt')

    version = __version__
    homepage = __homepage__

    page_size = 5

    def update(self):
        self._started = time.time()
        pruneTruncations()
        if 'page_size' in self.request:
            self.page_size = max(1, int(self.request['page_size']))
        self.history = IDatabaseHistory(self.jar)
        self.request.hold(Cleanup(self.history.cleanup))
        if 'page' in self.request:
            self.page = int(self.request['page'])
        elif 'tid' in self.request:
            tid = int(self.request['tid'], 0)
            self.page = self.findPage(p64(tid))
        else:
            self.page = 0
        self.last_page = max(0, len(self.history) - 1) // self.page_size
        if self.page > self.last_page:
            self.page = self.last_page
        self.last_idx = max(0, len(self.history) - self.page * self.page_size)
        self.first_idx = max(0, self.last_idx - self.page_size)

    def render(self):
        self.update()
        return self.template()

    def renderingTime(self):
        return '%.3fs |' % (time.time() - self._started)

    def getUrl(self, tid=None):
        url = "@@zodbbrowser_history"
        if tid is None and 'tid' in self.request:
            url += "?tid=" + self.request['tid']
        elif tid is not None:
            url += "?tid=0x%x" % tid
        return url

    def findPage(self, tid):
        try:
            pos = list(self.history.tids).index(tid)
        except ValueError:
            return 0
        else:
            return (len(self.history) - pos - 1) // self.page_size

    def listHistory(self):
        if 'tid' in self.request:
            requested_tid = p64(int(self.request['tid'], 0))
        else:
            requested_tid = None

        results = []
        for n, d in enumerate(self.history[self.first_idx:self.last_idx]):
            utid = u64(d.tid)
            ts = TimeStamp(d.tid).timeTime()
            utc_timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ts))
            local_timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
            try:
                user_location, user_id = d.user.split()
            except ValueError:
                user_location = None
                user_id = d.user
            if isinstance(user_location, bytes):
                user_location = user_location.decode('UTF-8', 'replace')
            if isinstance(user_id, bytes):
                user_id = user_id.decode('UTF-8', 'replace')
            description = d.description
            if isinstance(description, bytes):
                description = description.decode('UTF-8', 'replace')
            try:
                size = d._tend - d._tpos
            except AttributeError:
                size = None
            ext = d.extension if isinstance(d.extension, dict) else {}
            objects = []
            for record in d:
                obj = self.jar.get(record.oid)
                url = "@@zodbbrowser?oid=0x%x&tid=0x%x" % (u64(record.oid),
                                                           utid)
                objects.append(dict(
                    oid=u64(record.oid),
                    path=getObjectPath(obj, d.tid),
                    oid_repr=oid_repr(record.oid),
                    class_repr=getObjectType(obj),
                    url=url,
                    repr=IValueRenderer(obj).render(d.tid),
                ))
            if len(objects) == 1:
                summary = '1 object record'
            else:
                summary = '%d object records' % len(objects)
            if size is not None:
                summary += ' (%d bytes)' % size
            results.append(dict(
                index=(self.first_idx + n + 1),
                utc_timestamp=utc_timestamp,
                local_timestamp=local_timestamp,
                user_id=user_id,
                user_location=user_location,
                description=description,
                utid=utid,
                current=(d.tid == requested_tid),
                href=self.getUrl(tid=utid),
                size=size,
                summary=summary,
                hidden=(len(objects) > 5),
                objects=objects,
                **ext
            ))
        if results and not requested_tid and self.page == 0:
            results[-1]['current'] = True
        return results[::-1]


def getObjectType(obj):
    cls = getattr(obj, '__class__', None)
    if type(obj) is not cls:
        return '%s - %s' % (type(obj), cls)
    else:
        return str(cls)


def getObjectTypeShort(obj):
    cls = getattr(obj, '__class__', None)
    if type(obj) is not cls:
        return '%s - %s' % (type(obj).__name__, cls.__name__)
    else:
        return cls.__name__


def getObjectPath(obj, tid):
    path = []
    seen_root = False
    state = ZodbObjectState(obj, tid)
    while True:
        if state.isRoot():
            path.append('/')
            seen_root = True
        else:
            if path:
                path.append('/')
            if not state.getName() and state.getParentState() is None:
                # not using hex() because we don't want L suffixes for
                # 64-bit values
                path.append('0x%x' % state.getObjectId())
                break
            path.append(state.getName() or '???')
        state = state.getParentState()
        if state is None:
            if not seen_root:
                path.append('/')
                path.append('...')
                path.append('/')
            break
    return ''.join(path[::-1])

