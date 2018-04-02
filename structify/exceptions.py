class StructifyError(Exception):
    pass


class ParseError(StructifyError):
    pass


class StreamExhaustedError(ParseError):
    pass


class UnknownDependentFieldError(ParseError):
    pass


