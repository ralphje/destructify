import io

from destructify import ParsingContext, Structure, FixedLengthField, StringField
from tests import DestructifyTestCase


class ContextTest(DestructifyTestCase):
    def test_f_attribute(self):
        context = ParsingContext(parent=ParsingContext(field_values={'a': 3, 'b': 4},
                                                       parent=ParsingContext(field_values={'foo': 9, 'bar': 10})),
                                 field_values={'x': 1})
        self.assertEqual(1, context.f.x)
        self.assertEqual(3, context.f._.a)
        self.assertEqual(4, context.f._.b)
        self.assertEqual(9, context.f._root.foo)
        self.assertEqual(10, context.f._root.bar)
        self.assertIs(context, context.f._context)
