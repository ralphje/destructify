===============
Version history
===============

Releases
========

v0.1.0 (2019-02-17)
-------------------
This release features several new field types, and bugfixes from the previous release. Also some backwards-incompatible
changes were made.

* Added :attr:`Meta.byte_order`
* Added :meth:`Structure.as_cstruct()`
* Added :meth:`Structure.__len__`
* New field: :class:`structify.fields.ConditionalField`
* New field: :class:`structify.fields.EnumField`
* New field: :class:`structify.fields.BitField`
* New field: :class:`structify.fields.IntegerField`, renamed struct-based field to :class:`structify.fields.IntField`
* New field: :class:`structify.fields.FixedLengthStringField`
* New field: :class:`structify.fields.TerminatedStringField`
* Support negative lengths and padding in :class:`structify.fields.FixedLengthField`
* Support length in :class:`structify.fields.ArrayField`, renamed :attr:`ArrayField.size` to :attr:`ArrayField.count`
* Fixed :class:`structify.fields.StructureField` to use :class:`structify.Substream`
* Fixed double-closing a :class:`structify.Substream`

v0.0.1 (2018-04-07)
-------------------
Initial release.
