"""
zodbbrowser application interfaces.
"""

from zope.app.container.constraints import contains
from zope.app.container.interfaces import IContainer
from zope.app.container.interfaces import IContained
from zope.interface import Interface


class IContent(IContained):

    pass


class IZodbBrowser(IContainer):

    contains(IContent)

    pass
