from zope.interface import directlyProvides
from zope.publisher.browser import applySkin
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserSkinType

from zodbbrowser.interfaces import IZodbBrowser
from zope.app.rotterdam import Rotterdam


class IZodbBrowserSkin(IDefaultBrowserLayer):
     """Zodb Browser skin"""

directlyProvides(IZodbBrowserSkin, IBrowserSkinType)


def zodbBrowserTraverseSubscriber(event):
    """A subscriber to BeforeTraverseEvent.

    Sets the ZodbBrowser skin if the object traversed is ZodbBrowser.
    """
    if IZodbBrowser.providedBy(event.object):
        applySkin(event.request, IZodbBrowserSkin)
