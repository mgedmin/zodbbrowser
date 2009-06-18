from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.component import adapts
from zope.interface import Interface
from zope.security.proxy import removeSecurityProxy
from ZODB.utils import p64

from zodbbrowser.app import ZodbObject


class BaseZodbView(BrowserView):

    def obj(self):
        if 'oid' in self.request:
            oid = p64(int(self.request['oid']))
            return ZodbObject(removeSecurityProxy(self.context)._p_jar.get(oid))
        else:
            return ZodbObject(self.context)


class ZodbTreeView(BaseZodbView):
    """Zodb info view"""

    adapts(Interface, IBrowserRequest)

    template = ViewPageTemplateFile('templates/zodbtree.pt')

    def __call__(self):
        self.update()
        return self.template()

    def update(self, show_private=False, *args, **kw):
        pass


class ZodbInfoView(BaseZodbView):
    """Zodb info view"""

    adapts(Interface, IBrowserRequest)

    template = ViewPageTemplateFile('templates/zodbinfo.pt')

    def __call__(self):
        self.update()
        return self.template()

    def update(self, show_private=False, *args, **kw):
        pass

