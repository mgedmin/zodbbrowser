from cgi import escape

from zodbbrowser.interfaces import IValueRenderer


ADDED = 'added'
REMOVED = 'removed'
CHANGED = 'changed to'


def compareDicts(new, old):
    """Compare two state dictionaries, return dict."""
    diffs = {}
    for key, value in new.items():
        if key not in old:
            diffs[key] = (ADDED, value, None)
        elif old[key] != value:
            diffs[key] = (CHANGED, value, old[key])
    for key, value in old.items():
        if key not in new:
            diffs[key] = (REMOVED, None, value)
    return diffs


def isascii(s):
    """See if the string can be safely converted to unicode."""
    try:
        s.encode('ascii')
    except UnicodeError:
        return False
    else:
        return True


def compareDictsHTML(new, old, tid=None, indent=''):
    """Compare two state dictionaries, return HTML."""
    html = [indent + '<div class="diff">\n']
    diff = compareDicts(new, old)
    for key, (action, newvalue, oldvalue) in sorted(diff.items(),
                                            key=lambda (k, v): (type(k), k)):
        what = action.split()[0]
        html.append(indent + '  <div class="diffitem %s">\n' % escape(what))
        if isinstance(key, basestring) and isascii(key):
            html.append(indent + '    <strong>%s</strong>: ' % escape(key))
        else:
            html.append(indent + '    <strong>%s</strong>: '
                        % IValueRenderer(key).render(tid))
        if (action == CHANGED and isinstance(oldvalue, dict) and
            isinstance(newvalue, dict)):
            html.append('dictionary changed:\n')
            html.append(compareDictsHTML(newvalue, oldvalue, tid,
                                         indent=indent + '    '))
        else:
            html.append(action)
            html.append(' ')
            if action == REMOVED:
                value = oldvalue
            else:
                value = newvalue
            html.append(IValueRenderer(value).render(tid))
            html.append('\n')
        html.append(indent + '  </div>\n')
    html.append(indent + '</div>\n')
    return ''.join(html)

