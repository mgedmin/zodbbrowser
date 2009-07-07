from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.component import adapts
from zope.interface import Interface
from zope.security.proxy import removeSecurityProxy
from ZODB.utils import p64
from ZODB.utils import u64

from zodbbrowser.app import ZodbObject


class ZodbInfoView(BrowserView):
    """Zodb info view"""

    adapts(Interface, IBrowserRequest)

    template = ViewPageTemplateFile('templates/zodbinfo.pt')

    def __call__(self):
        self.update()
        return self.template()

    def update(self, show_private=False, *args, **kw):
        pass

    def obj(self):
        self.obj = None

        if 'oid' not in self.request:
            self.obj = ZodbObject(self.context)
        else:
            oid = p64(int(self.request['oid']))
            jar = removeSecurityProxy(self.context)._p_jar
            self.obj = ZodbObject(jar.get(oid))

        if 'tid' not in self.request:
            self.obj.load()
        else:
            self.obj.load(p64(int(self.request['tid'])))

        return self.obj

    def getObjectId(self):
        return u64(self.obj.obj._p_oid)

    def getObjectTid(self):
        return u64(self.obj.tid)

    def getObjectRequestedTid(self):
        if self.obj.requestedTid is None:
            return None
        else:
            return u64(self.obj.requestedTid)

    def getObjectType(self):
        return str(getattr(self.obj.obj, '__class__', None))
