class _NOT_PROVIDED_META(type):
    def __repr__(self):
        return "NOT_PROVIDED"


class NOT_PROVIDED(metaclass=_NOT_PROVIDED_META):
    pass


from destructify.parsing import *
from destructify.fields import *
from destructify.structures import *
from destructify import gui


__version__ = '0.1.0'
