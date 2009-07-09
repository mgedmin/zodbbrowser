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


def compareDictsHTML(new, old, tid=None):
    """Compare two state dictionaries, return HTML."""
    html = ['<div class="diff">\n']
    diff = compareDicts(new, old)
    for key, (action, newvalue, oldvalue) in sorted(diff.items()):
        what = action.split()[0]
        html.append('  <span class="diff %s">\n' % escape(what))
        html.append('    <strong>%s</strong>: ' % escape(key))
        if (action == CHANGED and isinstance(oldvalue, dict) and
            isinstance(newvalue, dict)):
            html.append('dictionary changed:\n')
            html.append('  </span>\n')
            html.append(compareDictsHTML(newvalue, oldvalue, tid))
        else:
            html.append(action)
            html.append(' ')
            if action == REMOVED:
                value = oldvalue
            else:
                value = newvalue
            html.append(IValueRenderer(value).render(tid))
            html.append('<br />\n')
            html.append('  </span>\n')
    html.append('</div>\n')
    return ''.join(html)

