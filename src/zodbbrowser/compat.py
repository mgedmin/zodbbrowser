try:
    basestring = basestring
except NameError:
    # Python 3
    basestring = str

try:
    from cStringIO import StringIO
    BytesIO = StringIO              # pragma: PY2
except ImportError:
    # Python 3
    from io import BytesIO, StringIO  # noqa

try:
    from html import escape
except ImportError:
    # Python 2
    from cgi import escape  # noqa
