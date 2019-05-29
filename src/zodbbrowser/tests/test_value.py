import unittest

from ZODB.utils import p64
from BTrees.OOBTree import OOBTree
from persistent import Persistent
from persistent.dict import PersistentDict
from zope.app.testing import setup
from zope.interface.verify import verifyObject
from zope.interface import implementer, alsoProvides, Interface
from zope.component import adapter, provideAdapter

from zodbbrowser.interfaces import IValueRenderer, IObjectHistory
from zodbbrowser.value import (
    GenericValue, TupleValue, ListValue, DictValue, PersistentValue,
    PersistentDictValue, ProvidesValue, StringValue, MAX_CACHE_SIZE,
    TRUNCATIONS, TRUNCATIONS_IN_ORDER, truncate, resetTruncations,
    pruneTruncations)


class OldStyle:
    pass


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


class ExplodingRepr(object):

    def __repr__(self):
        raise UnexpectedArbitraryError


class ExplodingClassNameRepr(ExplodingRepr):

    __class__ = ExplodingRepr()


class PersistentFrob(Persistent):
    _p_oid = p64(23)

    def __repr__(self):
        return '<PersistentFrob>'


class PersistentFrobNoRepr(Persistent):
    _p_oid = p64(23)


class PersistentThing(Persistent):
    _p_oid = p64(29)

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '<PersistentThing: %s>' % self.value


@adapter(PersistentThing)
@implementer(IObjectHistory)
class FakeObjectHistory(object):

    def __init__(self, context):
        pass

    def loadState(self, tid):
        return {'value': 'old'}


class Struct(object):
    pass


@adapter(Frob)
@implementer(IValueRenderer)
class FrobRenderer(object):

    def __init__(self, context):
        self.context = context

    def render(self, tid=None, can_link=True):
        if tid:
            return '<Frob [tid=%s]>' % tid
        else:
            return '<Frob>'


@adapter(Struct)
@implementer(IValueRenderer)
class StructRenderer(object):

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
        self.assertEqual(id1, 'tr1')
        self.assertEqual(id2, 'tr2')
        self.assertEqual(TRUNCATIONS, {'tr1': 'string 1', 'tr2': 'string 2'})
        self.assertEqual(list(TRUNCATIONS_IN_ORDER), ['tr1', 'tr2'])

    def test_pruneTruncations(self):
        for n in range(MAX_CACHE_SIZE + 3):
            truncate('a string')
        pruneTruncations()
        self.assertEqual(len(TRUNCATIONS), MAX_CACHE_SIZE)
        self.assertEqual(len(TRUNCATIONS_IN_ORDER), MAX_CACHE_SIZE)
        self.assertEqual(sorted(TRUNCATIONS_IN_ORDER), sorted(TRUNCATIONS))
        self.assertEqual(TRUNCATIONS_IN_ORDER[0], 'tr4')


class TestGenericValue(unittest.TestCase):

    def tearDown(self):
        resetTruncations()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, GenericValue(None))

    def test_simple_repr(self):
        for s in [None, '', 'xyzzy', b'\x17', u'\u1234']:
            self.assertEqual(GenericValue(s).render(), repr(s))

    def test_no_dunder_repr(self):
        # Fixes https://github.com/mgedmin/zodbbrowser/issues/6
        obj = OldStyle()
        self.assertEqual(GenericValue(obj)._repr(), repr(obj))

    def test_html_quoting(self):
        self.assertEqual(GenericValue('<html>').render(),
                         "'&lt;html&gt;'")

    def test_truncation(self):
        self.assertEqual(GenericValue('a very long string').render(limit=10),
                         """'a very lo<span id="tr1" class="truncated">...</span>""")
        self.assertEqual(TRUNCATIONS['tr1'], "ng string'")
        self.assertEqual(list(TRUNCATIONS_IN_ORDER), ['tr1'])

    def test_conteinerish_things(self):
        self.assertEqual(GenericValue([1, 2, 3]).render(),
                         "[1, 2, 3] (3 items)")
        self.assertEqual(GenericValue([1]).render(),
                         "[1] (1 item)")
        self.assertEqual(GenericValue([]).render(),
                         "[] (0 items)")

    def test_conteinerish_things_and_truncation(self):
        self.assertEqual(GenericValue([1, 2, 3]).render(limit=3),
                         '[1,<span id="tr1" class="truncated">...</span> (3 items)')

    def test_conteinerish_things_do_not_explode(self):
        self.assertEqual(GenericValue(ExplodingLen()).render(),
                         '&lt;ExplodingLen&gt;')

    def test_override_default_repr_of_Persistent(self):
        # https://bugs.launchpad.net/zodbbrowser/+bug/1087138
        self.assertEqual(GenericValue(PersistentFrobNoRepr()).render(),
                         '&lt;zodbbrowser.tests.test_value.PersistentFrobNoRepr'
                         ' with oid 0x17&gt;')

    def test_override_default_repr_of_BTree(self):
        # The pure-python implementation of BTrees (and buckets, and sets)
        # helpfully overrides __repr__ to drop the Py suffix from class names.
        self.assertEqual(GenericValue(OOBTree()).render(),
                         '&lt;BTrees.OOBTree.OOBTree with oid None&gt;'
                         ' (0 items)')

    def test_no_crashes(self):
        self.assertEqual(GenericValue(ExplodingRepr()).render(),
                         '&lt;unrepresentable ExplodingRepr&gt;')

    def test_srsly_no_crashes(self):
        self.assertEqual(GenericValue(ExplodingClassNameRepr()).render(),
                         '&lt;unrepresentable&gt;')


class TestStringValue(unittest.TestCase):

    # We don't want 'u' prefixes for unicode strings on Python 3.
    u = 'u' if str is bytes else ''

    def tearDown(self):
        resetTruncations()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, StringValue(()))

    def test_empty_string(self):
        self.assertEqual(StringValue('').render(), "''")

    def test_short_string(self):
        self.assertEqual(StringValue('xyzzy').render(), "'xyzzy'")

    def test_short_string_escaping(self):
        self.assertEqual(StringValue('x"y\'z\\z<y&').render(),
                         """'x"y\\'z\\\\z&lt;y&amp;'""")

    def test_short_string_control_char(self):
        self.assertEqual(StringValue('\x17').render(),
                         """'\\x17'""")

    def test_short_string_unicode(self):
        self.assertEqual(StringValue(u'\u1234').render(),
                         self.u + "'\u1234'")

    def test_short_string_truncation(self):
        self.assertEqual(StringValue('a very long string').render(limit=10),
                         """'a very lo<span id="tr1" class="truncated">...</span>""")
        self.assertEqual(TRUNCATIONS['tr1'], "ng string'")
        self.assertEqual(list(TRUNCATIONS_IN_ORDER), ['tr1'])

    def test_long_string(self):
        self.assertEqual(StringValue('line1 <\n'
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
        self.assertEqual(StringValue('line1\n'
                                     ' line2\n'
                                     '  line3\n'
                                     '\tline4\n'
                                     'line5\n').render(),
                         '\'<span class="struct">line1<br />'
                         '&nbsp;line2<br />'
                         '&nbsp;&nbsp;line3<br />'
                         '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;line4<br />'
                         'line5\'</span>')

    @unittest.skipIf(bytes is not str, "Only unicode strings exist on Python 3")
    def test_long_string_non_ascii(self):
        self.assertEqual(StringValue('line1\n'
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
        self.assertEqual(StringValue(u'line1\n'
                                     u'line2\n'
                                     u'line3 \xff\n'
                                     u'line4\n'
                                     u'line5\n').render(),
                         self.u + u'\'<span class="struct">line1<br />'
                         u'line2<br />'
                         u'line3 \xff<br />'
                         u'line4<br />'
                         u'line5\'</span>')

    def test_long_string_truncation(self):
        self.assertEqual(StringValue('line1\n'
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
        self.assertEqual(TRUNCATIONS['tr1'], "line6<br />line7")


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
        self.assertEqual(TupleValue(()).render(), '()')

    def test_single_item_tuple(self):
        self.assertEqual(TupleValue((Frob(), )).render(), '(<Frob>, )')

    def test_longer_tuples(self):
        self.assertEqual(TupleValue((1, Frob())).render(), '(1, <Frob>)')
        self.assertEqual(TupleValue((1, Frob(), 2)).render(),
                         '(1, <Frob>, 2)')

    def test_tid_is_preserved(self):
        self.assertEqual(TupleValue((Frob(), )).render(tid=42),
                         '(<Frob [tid=42]>, )')

    def test_nested_structs(self):
        self.assertEqual(TupleValue((Struct(), )).render(),
              '(<span class="struct"><span class="struct">Struct, )</span></span>')
        self.assertEqual(TupleValue((Struct(), Struct())).render(),
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
        self.assertEqual(ListValue([]).render(), '[]')

    def test_single_item_list(self):
        self.assertEqual(ListValue([Frob()]).render(), '[<Frob>]')

    def test_longer_lists(self):
        self.assertEqual(ListValue([1, Frob()]).render(), '[1, <Frob>]')
        self.assertEqual(ListValue([1, Frob(), 2]).render(),
                         '[1, <Frob>, 2]')

    def test_tid_is_preserved(self):
        self.assertEqual(ListValue([Frob()]).render(tid=42),
                         '[<Frob [tid=42]>]')

    def test_nested_structs(self):
        self.assertEqual(ListValue((Struct(), )).render(),
              '[<span class="struct"><span class="struct">Struct]</span></span>')
        self.assertEqual(ListValue((Struct(), Struct())).render(),
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
        self.assertEqual(DictValue({}).render(), '{}')

    def test_single_item_dict(self):
        self.assertEqual(DictValue({1: Frob()}).render(),
                         '{1: <Frob>}')

    def test_longer_dicts(self):
        self.assertEqual(DictValue({1: Frob(), 2: 3}).render(),
                         '{1: <Frob>, 2: 3}')
        self.assertEqual(DictValue({1: Frob(), 2: Frob(), 3: 4}).render(),
                         '{1: <Frob>, 2: <Frob>, 3: 4}')

    def test_truly_long_dicts(self):
        self.assertEqual(DictValue(
            {'some long key name': 'some long value',
             'some other long key name': 'some other long value'}).render(threshold=50),
            "{<span class=\"struct\">'some long key name': 'some long value',"
            "<br />'some other long key name': 'some other long value'}</span>")

    def test_nested_dicts(self):
        self.assertEqual(DictValue(
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
        self.assertEqual(DictValue({Frob(): Frob()}).render(tid=42),
                         '{<Frob [tid=42]>: <Frob [tid=42]>}')


class TestPersistentValue(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(GenericValue)
        provideAdapter(PersistentValue)

    def tearDown(self):
        setup.placelessTearDown()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, PersistentValue(None))

    def test_rendering(self):
        self.assertEqual(
            PersistentValue(PersistentFrob()).render(),
            '<a class="objlink" href="@@zodbbrowser?oid=0x17">'
            '&lt;PersistentFrob&gt;</a>')

    def test_old_value(self):
        provideAdapter(FakeObjectHistory)
        renderer = PersistentValue(PersistentThing('new'))
        self.assertEqual(
            renderer.render(tid=p64(42)),
            '<a class="objlink" href="@@zodbbrowser?oid=0x1d&amp;tid=0x2a">'
            '&lt;PersistentThing: old&gt;</a>')

    def test_tid_is_preserved(self):
        renderer = PersistentValue(PersistentFrob())
        self.assertEqual(
            renderer.render(tid=p64(42)),
            '<a class="objlink" href="@@zodbbrowser?oid=0x17&amp;tid=0x2a">'
            '&lt;PersistentFrob&gt;</a>')

    def test_rendering_no_nested_links(self):
        self.assertEqual(
            PersistentValue(PersistentFrob()).render(can_link=False),
            '&lt;PersistentFrob&gt;')


class TestPersistentDictValue(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideAdapter(GenericValue)
        provideAdapter(PersistentValue)

    def tearDown(self):
        setup.placelessTearDown()

    def test_rendering_no_nested_links(self):
        obj = PersistentDict({1: PersistentFrob()})
        obj._p_oid = p64(0x18)
        self.assertEqual(
            PersistentDictValue(obj).render(),
            '<a class="objlink" href="@@zodbbrowser?oid=0x18">'
            '{1: &lt;PersistentFrob&gt;}</a>')


class TestProvidesValue(unittest.TestCase):

    def tearDown(self):
        resetTruncations()

    def test_interface_compliance(self):
        verifyObject(IValueRenderer, ProvidesValue(None))

    def test_rendering(self):
        frob = Frob()
        alsoProvides(frob, ISomeInterface)
        renderer = ProvidesValue(frob.__provides__)
        self.assertEqual(renderer.render(),
            '&lt;Provides: zodbbrowser.tests.test_value.ISomeInterface&gt;')

    def test_rendering_multiple(self):
        frob = Frob()
        alsoProvides(frob, ISomeInterface, ISomeOther)
        renderer = ProvidesValue(frob.__provides__)
        self.assertEqual(renderer.render(),
            '&lt;Provides: zodbbrowser.tests.test_value.ISomeInterface,'
            ' zodbbrowser.tests.test_value.ISomeOther&gt;')

    def test_rendering_shortening(self):
        frob = Frob()
        alsoProvides(frob, ISomeInterface, ISomeOther)
        renderer = ProvidesValue(frob.__provides__)
        self.assertEqual(renderer.render(limit=42),
            '&lt;Provides: zodbbrowser.tests.test_value.IS'
            '<span id="tr1" class="truncated">...</span>')

