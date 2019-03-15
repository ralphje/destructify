import operator

OPERATIONS = {
    operator.lt: "<",
    operator.le: "<=",
    operator.eq: "==",
    operator.ne: "!=",
    operator.gt: ">",
    operator.ge: ">=",

    operator.not_: "not",
    # omitting is / is not

    operator.abs: "abs",
    operator.add: "+",
    operator.and_: "&",
    operator.floordiv: "//",
    # omitting __index__
    operator.invert: "~",
    operator.lshift: "<<",
    operator.mod: "%",
    operator.mul: "*",
    operator.matmul: "@",
    operator.neg: "-",
    operator.or_: "|",
    operator.pos: "+",
    operator.pow: "**",
    operator.rshift: ">>",
    operator.sub: "-",
    operator.truediv: "/",
    operator.xor: "^",

    # also omitting indexing

    divmod: "divmod",
    abs: "abs",
    #round: "round",
}


class Expression:
    def __lt__(self, other):
        return BinaryExpression(operator.lt, self, other)
    def __le__(self, other):
        return BinaryExpression(operator.le, self, other)
    def __eq__(self, other):
        return BinaryExpression(operator.eq, self, other)
    def __ne__(self, other):
        return BinaryExpression(operator.ne, self, other)
    def __gt__(self, other):
        return BinaryExpression(operator.gt, self, other)
    def __ge__(self, other):
        return BinaryExpression(operator.ge, self, other)

    def __add__(self, other):
        return BinaryExpression(operator.add, self, other)
    def __sub__(self, other):
        return BinaryExpression(operator.sub, self, other)
    def __mul__(self, other):
        return BinaryExpression(operator.mul, self, other)
    def __matmul__(self, other):
        return BinaryExpression(operator.matmul, self, other)
    def __truediv__(self, other):
        return BinaryExpression(operator.truediv, self, other)
    def __floordiv__(self, other):
        return BinaryExpression(operator.floordiv, self, other)
    def __mod__(self, other):
        return BinaryExpression(operator.mod, self, other)
    def __divmod__(self, other):
        return BinaryExpression(divmod, self, other)
    def __pow__(self, other):
        return BinaryExpression(operator.pow, self, other)
    def __lshift__(self, other):
        return BinaryExpression(operator.lshift, self, other)
    def __rshift__(self, other):
        return BinaryExpression(operator.rshift, self, other)
    def __and__(self, other):
        return BinaryExpression(operator.and_, self, other)
    def __xor__(self, other):
        return BinaryExpression(operator.xor, self, other)
    def __or__(self, other):
        return BinaryExpression(operator.or_, self, other)

    def __radd__(self, other):
        return BinaryExpression(operator.add, other, self)
    def __rsub__(self, other):
        return BinaryExpression(operator.sub, other, self)
    def __rmul__(self, other):
        return BinaryExpression(operator.mul, other, self)
    def __rmatmul__(self, other):
        return BinaryExpression(operator.matmul, other, self)
    def __rtruediv__(self, other):
        return BinaryExpression(operator.truediv, other, self)
    def __rfloordiv__(self, other):
        return BinaryExpression(operator.floordiv, other, self)
    def __rmod__(self, other):
        return BinaryExpression(operator.mod, other, self)
    def __rdivmod__(self, other):
        return BinaryExpression(divmod, other, self)
    def __rpow__(self, other):
        return BinaryExpression(operator.pow, other, self)
    def __rlshift__(self, other):
        return BinaryExpression(operator.lshift, other, self)
    def __rrshift__(self, other):
        return BinaryExpression(operator.rshift, other, self)
    def __rand__(self, other):
        return BinaryExpression(operator.and_, other, self)
    def __rxor__(self, other):
        return BinaryExpression(operator.xor, other, self)
    def __ror__(self, other):
        return BinaryExpression(operator.or_, other, self)

    def __neg__(self):
        return UnaryExpression(operator.neg, self)
    def __pos__(self):
        return UnaryExpression(operator.pos, self)
    def __abs__(self):
        return UnaryExpression(abs, self)
    def __invert__(self):
        return UnaryExpression(operator.invert, self)

    # round, trunc, floor, ceil


class BinaryExpression(Expression):
    def __init__(self, operator, lh, rh):
        self.operator = operator
        self.lh = lh
        self.rh = rh

    def __repr__(self):
        return "(%r %s %r)" % (self.lh, OPERATIONS[self.operator], self.rh)

    def __str__(self):
        return "(%s %s %s)" % (self.lh, OPERATIONS[self.operator], self.rh)

    def __call__(self, obj, *args):
        lh = self.lh(obj) if callable(self.lh) else self.lh
        rh = self.rh(obj) if callable(self.rh) else self.rh
        return self.operator(lh, rh)


class UnaryExpression(Expression):
    def __init__(self, operator, operand):
        self.operator = operator
        self.operand = operand

    def __repr__(self):
        return "(%s %r)" % (OPERATIONS[self.operator], self.operand)

    def __str__(self):
        return "(%s %s)" % (OPERATIONS[self.operator], self.operand)

    def __call__(self, obj, *args):
        operand = self.operand(obj) if callable(self.operand) else self.operand
        return self.operator(operand)


class Element(Expression):
    def __init__(self, name, attribute=None, parent=None):
        self.__name = name
        self.__attribute = attribute
        self.__parent = parent

    def __repr__(self):
        if self.__parent is None:
            return repr(self.__name)
        else:
            return "%r.%s" % (self.__parent, self.__attribute)

    def __str__(self):
        if self.__parent is None:
            return str(self.__name)
        else:
            return "%s.%s" % (self.__parent, self.__attribute)

    def __call__(self, obj, *args):
        if self.__parent is None:
            return obj
        else:
            return getattr(self.__parent(obj), self.__attribute)

    def __getattr__(self, item):
        return self.__class__(self.__name, item, self)

    def __getitem__(self, item):
        return self.__class__(self.__name, item, self)


class Function(Expression):
    def __init__(self, function, name=None, operand=None):
        self.__function = function
        self.__name = name
        self.__operand = operand

    def __repr__(self):
        if self.__operand is None:
            return self.__name if self.__name is not None else self.__function.__name__
        else:
            return "%s(%r)" % (self.__function.__name__, self.__operand)

    def __str__(self):
        if self.__operand is None:
            return self.__name if self.__name is not None else self.__function.__name__
        else:
            return "%s(%s)" % (self.__function.__name__, self.__operand)

    def __call__(self, operand, *args):
        if self.__operand is None:
            return self.__class__(self.__function, operand) if callable(operand) else operand
        else:
            return self.__function(self.__operand(operand) if callable(self.__operand) else self.__operand)


this = Element('this')
len_ = Function(len)
sum_ = Function(sum)
min_ = Function(min)
max_ = Function(max)
