import unittest2 as unittest
import sys

from ZODB.utils import p64
from persistent import Persistent
from zope.app.testing import setup
from zope.interface.verify import verifyObject
from zope.interface import implements, alsoProvides, Interface
from zope.component import adapts, provideAdapter

from zodbbrowser.interfaces import IValueRenderer
from zodbbrowser.value import (GenericValue, TupleValue, ListValue, DictValue,
                               PersistentValue, ProvidesValue, StringValue,
                               MAX_CACHE_SIZE,
                               TRUNCATIONS, TRUNCATIONS_IN_ORDER, truncate,
                               resetTruncations, pruneTruncations)


class Frob(object):
    pass


class UnexpectedArbitraryError(Exception):
    pass


class ISomeInterface(Interface):
    pass


class ISomeOther(Interface):
    pass


class ExplodingLen(object):

    def __repr__(self):
        return '<ExplodingLen>'

    def __len__(self):
        raise UnexpectedArbitraryError


class PersistentFrob(Persistent):
    _p_oid = p64(23)

    def __repr__(self):
        return '<PersistentFrob>'


class Struct(object):
    pass


class FrobRenderer(object):
    adapts(Frob)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, can_link=True):
        if tid:
            return '<Frob [tid=%s]>' % tid
        else:
            return '<Frob>'


class StructRenderer(object):
    adapts(Struct)
    implements(IValueRenderer)

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, can_link=True):
        return '<span class="struct">Struct</span>'


class TestTruncations(unittest.TestCase):

    def tearDown(self):
        resetTruncations()

    def test_truncate(self):
        id1 = truncate('string 1')
        id2 = truncate('string 2')
        self.assertEquals(id1, 'tr1')
        self.assertEquals(id2, 'tr2')
        self.assertEquals(TRUNCATIONS, {'tr1': 'string 1', 'tr2': 'string 2'})
        self.assertEquals(list(TRUNCATIONS_IN_ORDER), ['tr1', 'tr2'])

    def test_pruneTruncations(self):
        for n in range(MAX_CACHE_SIZE + 3):
            truncate('a string')
        pruneTruncations()
        self.assertEquals(len(TRUNCATIONS), MAX_CACHE_SIZE)
        self.assertEquals(len(TRUNCATIONS_IN_ORDER), MAX_CACHE_SIZE)
        self.assertEquals(sorted(TRUNCATIONS_IN_ORDER), sorted(TRUNCATIONS))
        self.assertEquals(TRUNCATIONS_IN_ORDER[0], 'tr4')


class TestGenericValue(unittest.TestCase):

    def tearDown(self):
        resetTruncations()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, GenericValue(None))

    def test_simple_repr(self):
        for s in [None, '', 'xyzzy', '\x17', u'\u1234']:
            self.assertEquals(GenericValue(s).render(), repr(s))

    def test_html_quoting(self):
        self.assertEquals(GenericValue('<html>').render(),
                          "'&lt;html&gt;'")

    def test_truncation(self):
        self.assertEquals(GenericValue('a very long string').render(limit=10),
                          """'a very lo<span id="tr1" class="truncated">...</span>""")
        self.assertEquals(TRUNCATIONS['tr1'], "ng string'")
        self.assertEquals(list(TRUNCATIONS_IN_ORDER), ['tr1'])

    def test_conteinerish_things(self):
        self.assertEquals(GenericValue([1, 2, 3]).render(),
                          "[1, 2, 3] (3 items)")
        self.assertEquals(GenericValue([1]).render(),
                          "[1] (1 item)")
        self.assertEquals(GenericValue([]).render(),
                          "[] (0 items)")

    def test_conteinerish_things_and_truncation(self):
        self.assertEquals(GenericValue([1, 2, 3]).render(limit=3),
                          '[1,<span id="tr1" class="truncated">...</span> (3 items)')

    def test_conteinerish_things_do_not_explode(self):
        self.assertEquals(GenericValue(ExplodingLen()).render(),
                          '&lt;ExplodingLen&gt;')


class TestStringValue(unittest.TestCase):

    def tearDown(self):
        resetTruncations()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, StringValue(()))

    def test_empty_string(self):
        self.assertEquals(StringValue('').render(), "''")

    def test_short_string(self):
        self.assertEquals(StringValue('xyzzy').render(), "'xyzzy'")

    def test_short_string_escaping(self):
        self.assertEquals(StringValue('x"y\'z\\z<y&').render(),
                          """'x"y\\'z\\\\z&lt;y&amp;'""")

    def test_short_string_control_char(self):
        self.assertEquals(StringValue('\x17').render(),
                          """'\\x17'""")

    def test_short_string_unicode(self):
        self.assertEquals(StringValue(u'\u1234').render(),
                          """u'\u1234'""")

    def test_short_string_truncation(self):
        self.assertEquals(StringValue('a very long string').render(limit=10),
                          """'a very lo<span id="tr1" class="truncated">...</span>""")
        self.assertEquals(TRUNCATIONS['tr1'], "ng string'")
        self.assertEquals(list(TRUNCATIONS_IN_ORDER), ['tr1'])

    def test_long_string(self):
        self.assertEquals(StringValue('line1 <\n'
                                      'line2 &\n'
                                      'line3\n'
                                      'line4\n'
                                      'line5\n').render(),
                          '\'<span class="struct">line1 &lt;<br />'
                          'line2 &amp;<br />'
                          'line3<br />'
                          'line4<br />'
                          'line5\'</span>')

    def test_long_string_indentation(self):
        self.assertEquals(StringValue('line1\n'
                                      ' line2\n'
                                      '  line3\n'
                                      '\tline4\n'
                                      'line5\n').render(),
                          '\'<span class="struct">line1<br />'
                          '&nbsp;line2<br />'
                          '&nbsp;&nbsp;line3<br />'
                          '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;line4<br />'
                          'line5\'</span>')

    def test_long_string_non_ascii(self):
        self.assertEquals(StringValue('line1\n'
                                      'line2\n'
                                      'line3 \xff\n'
                                      'line4\n'
                                      'line5\n').render(),
                          '\'<span class="struct">line1<br />'
                          'line2<br />'
                          'line3 \\xff<br />'
                          'line4<br />'
                          'line5\'</span>')

    def test_long_string_unicode(self):
        self.assertEquals(StringValue(u'line1\n'
                                      u'line2\n'
                                      u'line3 \xff\n'
                                      u'line4\n'
                                      u'line5\n').render(),
                          u'u\'<span class="struct">line1<br />'
                          u'line2<br />'
                          u'line3 \xff<br />'
                          u'line4<br />'
                          u'line5\'</span>')

    def test_long_string_truncation(self):
        self.assertEquals(StringValue('line1\n'
                                      'line2\n'
                                      'line3\n'
                                      'line4\n'
                                      'line5\n'
                                      'line6\n'
                                      'line7').render(limit=10),
                          '\'<span class="struct">line1<br />'
                          'line2<br />'
                          'line3<br />'
                          'line4<br />'
                          'line5<br />'
                          '<span id="tr1" class="truncated">...</span>\'</span>')
        self.assertEquals(TRUNCATIONS['tr1'], "line6<br />line7")


class TestTupleValue(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(GenericValue)
        provideAdapter(FrobRenderer)
        provideAdapter(StructRenderer)

    def tearDown(self):
        setup.placelessTearDown()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, TupleValue(()))

    def test_empty_tuple(self):
        self.assertEquals(TupleValue(()).render(), '()')

    def test_single_item_tuple(self):
        self.assertEquals(TupleValue((Frob(), )).render(), '(<Frob>, )')

    def test_longer_tuples(self):
        self.assertEquals(TupleValue((1, Frob())).render(), '(1, <Frob>)')
        self.assertEquals(TupleValue((1, Frob(), 2)).render(),
                          '(1, <Frob>, 2)')

    def test_tid_is_preserved(self):
        self.assertEquals(TupleValue((Frob(), )).render(tid=42),
                          '(<Frob [tid=42]>, )')

    def test_nested_structs(self):
        self.assertEquals(TupleValue((Struct(), )).render(),
              '(<span class="struct"><span class="struct">Struct, )</span></span>')
        self.assertEquals(TupleValue((Struct(), Struct())).render(),
              '(<span class="struct"><span class="struct">Struct,</span>'
              '<br /><span class="struct">Struct)</span></span>')


class TestListValue(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(GenericValue)
        provideAdapter(FrobRenderer)
        provideAdapter(StructRenderer)

    def tearDown(self):
        setup.placelessTearDown()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, ListValue([]))

    def test_empty_list(self):
        self.assertEquals(ListValue([]).render(), '[]')

    def test_single_item_list(self):
        self.assertEquals(ListValue([Frob()]).render(), '[<Frob>]')

    def test_longer_lists(self):
        self.assertEquals(ListValue([1, Frob()]).render(), '[1, <Frob>]')
        self.assertEquals(ListValue([1, Frob(), 2]).render(),
                          '[1, <Frob>, 2]')

    def test_tid_is_preserved(self):
        self.assertEquals(ListValue([Frob()]).render(tid=42),
                          '[<Frob [tid=42]>]')

    def test_nested_structs(self):
        self.assertEquals(ListValue((Struct(), )).render(),
              '[<span class="struct"><span class="struct">Struct]</span></span>')
        self.assertEquals(ListValue((Struct(), Struct())).render(),
              '[<span class="struct"><span class="struct">Struct,</span>'
              '<br /><span class="struct">Struct]</span></span>')



class TestDictValue(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(GenericValue)
        provideAdapter(FrobRenderer)
        provideAdapter(StructRenderer)
        provideAdapter(DictValue)
        self.addTypeEqualityFunc(str, 'assertMultiLineEqual')

    def tearDown(self):
        setup.placelessTearDown()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, DictValue({}))

    def test_empty_dict(self):
        self.assertEquals(DictValue({}).render(), '{}')

    def test_single_item_dict(self):
        self.assertEquals(DictValue({1: Frob()}).render(),
                          '{1: <Frob>}')

    def test_longer_dicts(self):
        self.assertEquals(DictValue({1: Frob(), 2: 3}).render(),
                          '{1: <Frob>, 2: 3}')
        self.assertEquals(DictValue({1: Frob(), 2: Frob(), 3: 4}).render(),
                          '{1: <Frob>, 2: <Frob>, 3: 4}')

    def test_truly_long_dicts(self):
        self.assertEquals(DictValue(
            {'some long key name': 'some long value',
             'some other long key name': 'some other long value'}).render(threshold=50),
           "{<span class=\"struct\">'some long key name': 'some long value',"
           "<br />'some other long key name': 'some other long value'}</span>")

    def test_nested_dicts(self):
        self.assertEquals(DictValue(
            {'A': {'some long key name': 'some long value',
                   'some other long key name': 'some other long value',
                   'struct': Struct()},
             'B': ['something else entirely']}).render().replace('<br />', '\n<br />'),
           "{<span class=\"struct\">'A':"
                " {<span class=\"struct\">'some long key name':"
                " 'some long value',\n"
                "<br />'some other long key name':"
                " 'some other long value',\n"
                "<br />'struct':"
                " <span class=\"struct\">Struct}</span>,</span>\n"
           "<br />'B': ['something else entirely'] (1 item)}</span>")

    def test_tid_is_preserved(self):
        self.assertEquals(DictValue({Frob(): Frob()}).render(tid=42),
                          '{<Frob [tid=42]>: <Frob [tid=42]>}')


class TestPersistentValue(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(GenericValue)

    def tearDown(self):
        setup.placelessTearDown()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, PersistentValue(None))

    def test_rendering(self):
        self.assertEquals(PersistentValue(PersistentFrob()).render(),
                  '<a class="objlink" href="@@zodbbrowser?oid=23">'
                          '&lt;PersistentFrob&gt;</a>')

    def test_tid_is_preserved(self):
        renderer = PersistentValue(PersistentFrob())
        self.assertEquals(renderer.render(tid=p64(42)),
                  '<a class="objlink" href="@@zodbbrowser?oid=23&amp;tid=42">'
                          '&lt;PersistentFrob&gt;</a>')


class TestProvidesValue(unittest.TestCase):

    def tearDown(self):
        resetTruncations()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, ProvidesValue(None))

    def test_rendering(self):
        frob = Frob()
        alsoProvides(frob, ISomeInterface)
        renderer = ProvidesValue(frob.__provides__)
        self.assertEquals(renderer.render(),
            '&lt;Provides: zodbbrowser.tests.test_value.ISomeInterface&gt;')

    def test_rendering_multiple(self):
        frob = Frob()
        alsoProvides(frob, ISomeInterface, ISomeOther)
        renderer = ProvidesValue(frob.__provides__)
        self.assertEquals(renderer.render(),
            '&lt;Provides: zodbbrowser.tests.test_value.ISomeInterface,'
            ' zodbbrowser.tests.test_value.ISomeOther&gt;')

    def test_rendering_shortening(self):
        frob = Frob()
        alsoProvides(frob, ISomeInterface, ISomeOther)
        renderer = ProvidesValue(frob.__provides__)
        self.assertEquals(renderer.render(limit=42),
            '&lt;Provides: zodbbrowser.tests.test_value.IS'
            '<span id="tr1" class="truncated">...</span>')


def test_suite():
    this = sys.modules[__name__]
    return unittest.defaultTestLoader.loadTestsFromModule(this)

