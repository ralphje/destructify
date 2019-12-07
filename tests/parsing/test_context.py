import io

from destructify import ParsingContext, Structure, FixedLengthField, StringField, StructureField
from tests import DestructifyTestCase


class ContextTest(DestructifyTestCase):
    def test_f_attribute(self):
        context = ParsingContext(
            parent=ParsingContext(
                parent=ParsingContext()._add_values({'foo': 9, 'bar': 10})
            )._add_values({'a': 3, 'b': 4})
        )._add_values({'x': 1})

        self.assertEqual(1, context.f.x)
        self.assertEqual(3, context.f._.a)
        self.assertEqual(4, context.f._.b)
        self.assertEqual(9, context.f._root.foo)
        self.assertEqual(10, context.f._root.bar)
        self.assertIs(context, context.f._context)

    def test_f_attribute_no_parent(self):
        context = ParsingContext()._add_values({'x': 1})

        self.assertEqual(1, context.f.x)
        self.assertEqual(None, context.f._)
        self.assertIs(context.f, context.f._root)


class SubContextTest(DestructifyTestCase):
    def test_child_context(self):
        context = ParsingContext()._add_values({'x': 1})
        subcontext = context.fields['x'].create_subcontext()
        self.assertIs(context.fields['x'].subcontext, subcontext)

    def test_child_context_different_class(self):
        class SubContext(ParsingContext):
            pass

        context = SubContext()._add_values({'x': 1})
        subcontext = context.fields['x'].create_subcontext()
        self.assertIsInstance(subcontext, SubContext)

    def test_child_context_capture_raw(self):
        context = ParsingContext(capture_raw=True)._add_values({'x': 1})
        subcontext = context.fields['x'].create_subcontext()
        self.assertFalse(subcontext.capture_raw)


class CaptureRawTest(DestructifyTestCase):
    def test_capture_raw_from_meta(self):
        class S(Structure):
            a = FixedLengthField(length=6)

            class Meta:
                capture_raw = True

        s = S.from_bytes(b"abcdef")
        self.assertTrue(hasattr(s._context.stream, 'cache_read_last'))
        self.assertEqual(b"abcdef", s._context.fields['a'].raw)

    def test_capture_raw_from_context(self):
        class S(Structure):
            a = FixedLengthField(length=6)

        s = S.from_bytes(b"abcdef", ParsingContext(capture_raw=True))
        self.assertFalse(hasattr(s._context.stream, 'cache_read_last'))
        self.assertEqual(b"abcdef", s._context.fields['a'].raw)

    def test_capture_raw_nested(self):
        class Inner(Structure):
            a = FixedLengthField(length=2)

        class S(Structure):
            a = StructureField(Inner)

            class Meta:
                capture_raw = True

        s = S.from_bytes(b"ab")
        self.assertEqual(b"ab", s._context.fields['a'].raw)
        self.assertEqual(None, s._context.fields['a'].subcontext.fields['a'].raw)

    def test_capture_raw_nested_with_subclass_of_context(self):
        class SubContext(ParsingContext):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.capture_raw = True

        class Inner(Structure):
            o = FixedLengthField(length=2)
            a = FixedLengthField(length=2)

        class S(Structure):
            o = FixedLengthField(length=2)
            a = StructureField(Inner)

            class Meta:
                capture_raw = True

        s = S.from_bytes(b"abcdef", SubContext())
        self.assertEqual(b"ab", s._context.fields['o'].raw)
        self.assertEqual(b"cdef", s._context.fields['a'].raw)
        self.assertEqual(b"cd", s._context.fields['a'].subcontext.fields['o'].raw)
        self.assertEqual(b"ef", s._context.fields['a'].subcontext.fields['a'].raw)
