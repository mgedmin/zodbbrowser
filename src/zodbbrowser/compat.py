try:
    basestring = basestring
except NameError:
    # Python 3
    basestring = str

try:
    from cStringIO import StringIO
except ImportError:
    # Python 3
    from io import StringIO  # noqa
