from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.component import adapts
from zope.interface import Interface

from zodbbrowser.app import ZodbObject


class ZodbTreeView(BrowserView):
    """Zodb info view"""

    adapts(Interface, IBrowserRequest)

    template = ViewPageTemplateFile('templates/zodbtree.pt')

    # TODO(zv): create obj on init?
    def obj(self):
        return ZodbObject(self.context)

    def __call__(self):

        self.update()
        return self.template()

    def update(self, show_private=False, *args, **kw):
        pass


class ZodbInfoView(BrowserView):
    """Zodb info view"""

    adapts(Interface, IBrowserRequest)

    template = ViewPageTemplateFile('templates/zodbinfo.pt')

    # TODO(zv): create obj on init?
    def obj(self):
        return ZodbObject(self.context)

    def __call__(self):

        self.update()
        return self.template()

    def update(self, show_private=False, *args, **kw):
        pass
