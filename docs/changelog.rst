===============
Version history
===============
.. module:: destructify

Releases
========

v0.2.0 (unreleased)
-------------------
This release adds more field types and further improves on existing code. It also extends the documentation
significantly.

* Added :attr:`StructureOptions.encoding`
* Added :attr:`StructureOptions.alignment`, :attr:`Field.offset` and :attr:`Field.skip`, implemented by
  :class:`Field.seek_start`
* Added :attr:`BytesField.terminator_handler`
* New field :class:`BytesField`, merging the features of :class:`FixedLengthField` and :class:`TerminatedField`. These
  fields will remain as subclasses.
* New field: :class:`MagicField`
* New field: :class:`SwitchField`
* New field: :class:`VariableLengthQuantityField`
* Merged :class:`FixedLengthStringField` and :class:`TerminatedStringField` into :class:`StringField`
* Renamed hook functions :meth:`Field.from_bytes` and :meth:`Field.to_bytes` to
  :meth:`BytesField.to_python` and :meth:`BytesField.from_python`, avoiding confusion with
  :meth:`Structure.from_bytes` and :meth:`Structure.to_bytes`
* Removed all byte-order specific subclasses from :class:`StructField`.
* Add option to :class:`ParsingContext` to capture the raw bytes, available in :attr:`ParsingContext.fields`
* Add :attr:`ParsingContext.fields` for information about the parsing structure.
* Added :attr:`ParsingContext.f` for raw attribute access.
* Added :class:`this` for quick construction of lambdas
* :class:`Substream` is now a wrapper instead of a full-fletched BufferedReader

v0.1.0 (2019-02-17)
-------------------
This release features several new field types, and bugfixes from the previous release. Also some backwards-incompatible
changes were made.

* Added :attr:`StructureOptions.byte_order`
* Added :meth:`Structure.as_cstruct()`
* Added :meth:`Structure.__len__`
* Added :meth:`Structure.full_name`
* :class:`FieldContext` is now :class:`ParsingContext`
* New field: :class:`ConditionalField`
* New field: :class:`EnumField`
* New field: :class:`BitField`
* New field: :class:`IntegerField`, renamed struct-based field to :class:`IntField`
* New field: :class:`FixedLengthStringField`
* New field: :class:`TerminatedStringField`
* Support strict, negative lengths and padding in :class:`structify.fields.FixedLengthField`
* Support length in :class:`structify.fields.ArrayField`, renamed :attr:`ArrayField.size` to :attr:`ArrayField.count`
* Support step :class:`structify.fields.TerminatedField`
* Fixed :class:`structify.fields.StructureField` to use :class:`structify.Substream`
* Fixed double-closing a :class:`structify.Substream`

v0.0.1 (2018-04-07)
-------------------
Initial release.
