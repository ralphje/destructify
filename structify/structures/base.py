import inspect
import io

from structify.structures.options import StructureOptions


class StructureBase(type):
    def __new__(cls, name, bases, namespace, **kwargs):
        # Ensure initialization is only performed for subclasses of Structure
        # (excluding Structure class itself).
        parents = [b for b in bases if isinstance(b, StructureBase)]
        if not parents:
            return super().__new__(cls, name, bases, namespace)

        # Create the class.
        module = namespace.pop('__module__')
        new_attrs = {'__module__': module}
        classcell = namespace.pop('__classcell__', None)
        if classcell is not None:
            new_attrs['__classcell__'] = classcell
        new_class = super().__new__(cls, name, bases, new_attrs, **kwargs)

        attr_meta = namespace.pop('Meta', None)
        meta = attr_meta or getattr(new_class, 'Meta', None)
        new_class.add_to_class('_meta', StructureOptions(meta))

        # Add all attributes to the class.
        for obj_name, obj in namespace.items():
            new_class.add_to_class(obj_name, obj)

        return new_class

    def add_to_class(cls, name, value):
        # We should call the contribute_to_class method only if it's bound
        if not inspect.isclass(value) and hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)


class Structure(metaclass=StructureBase):
    def __init__(self, **kwargs):
        """A base structure. It is the basis for all structures. You can pass in keyword arguments to provide
        different values than the field's defaults.

        :param kwargs:
        """
        for field in self._meta.fields:
            field.structure = self
            try:
                val = kwargs.pop(field.name)
            except KeyError:
                val = field.get_default()
            setattr(self, field.name, val)

        super().__init__()

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self)

    def __str__(self):
        values = []
        for field in self._meta.fields:
            values.append("%s=%r" % (field.name, getattr(self, field.name)))
        return '%s(%s)' % (self.__class__.__name__, ", ".join(values))

    def __bytes__(self):
        return self.to_bytes()

    @classmethod
    def from_stream(cls, stream):
        attrs = {}
        total_consumed = 0
        for field in cls._meta.fields:
            field._parse_state = attrs
            result, consumed = field.from_stream(stream)
            attrs[field.name] = result
            total_consumed += consumed
            stream.seek(total_consumed)

        return cls(**attrs), total_consumed

    def to_stream(self, stream):
        total_written = 0
        for field in self._meta.fields:
            total_written += field.to_stream(stream, getattr(self, field.name))

        return total_written

    @classmethod
    def from_bytes(cls, bytes):
        return cls.from_stream(io.BytesIO(bytes))[0]

    def to_bytes(self):
        bytesio = io.BytesIO()
        self.to_stream(bytesio)
        return bytesio.getvalue()

