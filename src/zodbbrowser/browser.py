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
from zodbbrowser.object import ZodbObject


class ZodbHelpView(BrowserView):
    """Zodb help view"""

    version = __version__
    homepage = __homepage__


class ZodbInfoView(BrowserView):
    """Zodb browser view"""

    adapts(Interface, IBrowserRequest)

    template = ViewPageTemplateFile('templates/zodbinfo.pt')

    version = __version__
    homepage = __homepage__

    def __call__(self):
        return self.template()

    @property
    def root_oid(self):
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
        oid = self.root_oid
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

    def obj(self):
        self.obj = None

        if 'oid' not in self.request and isinstance(self.context, Persistent):
            self.obj = ZodbObject(self.context)
        else:
            oid = p64(int(self.request.get('oid', self.root_oid)))
            jar = self.jar()
            self.obj = ZodbObject(jar.get(oid))

        if 'tid' not in self.request:
            self.obj.load()
        else:
            self.obj.load(p64(int(self.request['tid'])))

        return self.obj

    def getObjectId(self):
        return self.obj.getObjectId()

    def getObjectTid(self):
        return u64(self.obj.tid)

    def getObjectTidNice(self):
        return self.tidToTimestamp(self.obj.tid)

    def getObjectRequestedTid(self):
        if self.obj.requestedTid is None:
            return None
        else:
            return u64(self.obj.requestedTid)

    def getObjectRequestedTidNice(self):
        if self.obj.requestedTid is None:
            return None
        else:
            return self.tidToTimestamp(self.obj.requestedTid)

    def getObjectType(self):
        return str(getattr(self.obj.obj, '__class__', None))

    def getUrl(self, oid=None):
        url = "@@zodbbrowser?oid="
        if oid is not None:
            url += str(oid)
        else:
            url += str(self.obj.getObjectId())
        if 'tid' in self.request:
            url += "&tid=" + self.request['tid']
        return url

    def getPath(self):
        path = []
        object = self.obj
        while True:
            if object.isRoot():
                seen_root = True
                path.append('')
            else:
                path.append(object.getName())
            parent = object.getParent()
            if parent is None:
                break
            object = ZodbObject(parent)
            object.load()
        return '/'.join(reversed(path))

    def getBreadcrumbs(self):
        breadcrumbs = []
        object = self.obj
        seen_root = False
        while True:
            if object.isRoot():
                seen_root = True
                breadcrumb = '<a href="%s">/</a>' % (
                                    escape(self.getUrl(object.getObjectId())))
            else:
                breadcrumb = '<a href="%s">%s</a>' % (
                                    escape(self.getUrl(object.getObjectId())),
                                    object.getName())
                if breadcrumbs:
                    breadcrumb += '/'
            breadcrumbs.append(breadcrumb)
            parent = object.getParent()
            if parent is None:
                break
            object = ZodbObject(parent)
            object.load()

        if not seen_root:
            breadcrumbs.append('<a href="%s">/</a>' %
                                    escape(self.getUrl(self.root_oid)))
        return ''.join(reversed(breadcrumbs))

    def tidToTimestamp(self, tid):
        if isinstance(tid, str) and len(tid) == 8:
            return str(TimeStamp(tid))
        return tid_repr(tid)
