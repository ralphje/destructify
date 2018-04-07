from bisect import bisect


class StructureOptions:
    def __init__(self, meta=None):
        self.meta = meta

        self.structure = None
        self.fields = []
        self.object_name = None
        self.structure_name = None

    def contribute_to_class(self, cls, name):
        setattr(cls, '_meta', self)

        self.structure = cls

        self.object_name = cls.__name__
        self.structure_name = self.object_name.lower()

        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                # Ignore any private attributes we don't care about.
                if name.startswith('_'):
                    del meta_attrs[name]
            for attr_name in ('object_name', 'structure_name'):
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError("'class Meta' got invalid attribute(s): %s" % ','.join(meta_attrs))
        del self.meta

    def add_field(self, field):
        self.fields.insert(bisect(self.fields, field), field)

    def get_field_by_name(self, name):
        for field in self.fields:
            if field.name == name:
                return field
        raise KeyError("Field not found")

    def initialize_fields(self):
        for field in self.fields:
            field.initialize()
