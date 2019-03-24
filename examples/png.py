import destructify
import enum
from binascii import crc32


class ChunkType(destructify.PseudoMemberEnumMixin, enum.Enum):
    IHDR = "IHDR"
    IEND = "IEND"
    TEXT = "tEXt"
    PHYS = "pHYs"
    PLTE = "PLTE"


class ColorType(enum.IntEnum):
    GrayScale = 0
    RGB = 2
    Palette = 3
    GrayScaleAlpha = 4
    RGBA = 6


class InterlaceMethod(enum.IntEnum):
    NoInterlace = 0
    Adam7 = 1


class PngChunk_IHDR(destructify.Structure):
    width = destructify.IntegerField(4, "big")
    height = destructify.IntegerField(4, "big")
    bit_depth = destructify.IntegerField(1)
    color_type = destructify.EnumField(destructify.IntegerField(1), ColorType)
    compression_method = destructify.IntegerField(1)
    filter_method = destructify.IntegerField(1)
    interlace_method = destructify.EnumField(destructify.IntegerField(1), InterlaceMethod)


class PngChunk_tEXt(destructify.Structure):
    keyword = destructify.StringField(terminator=b"\x00", encoding="latin1")
    text = destructify.StringField(length=lambda f: f._.length - (len(f.keyword) + 1), encoding="latin1")


class PaletteEntry(destructify.Structure):
    red = destructify.IntegerField(length=1)
    green = destructify.IntegerField(length=1)
    blue = destructify.IntegerField(length=1)


class PngChunk_PLTE(destructify.Structure):
    palettes = destructify.ArrayField(destructify.StructureField(PaletteEntry), length=-1)


class PhysUnit(enum.IntEnum):
    Unknown = 0
    Meter = 1


class PngChunk_pHYs(destructify.Structure):
    pixels_per_unit_x = destructify.IntegerField(4, "big")
    pixels_per_unit_y = destructify.IntegerField(4, "big")
    unit = destructify.EnumField(destructify.IntegerField(1), PhysUnit)


def calculate_crc(f):
    crc = 0
    crc = crc32(f._context.fields['chunk_type'].raw, crc)
    crc = crc32(f._context.fields['chunk_data'].raw, crc)
    return crc


class PngChunk(destructify.Structure):
    length = destructify.IntegerField(4, "big")
    chunk_type = destructify.EnumField(destructify.StringField(length=4, encoding="ascii"), enum=ChunkType)
    chunk_data = destructify.SwitchField(
        cases={
            ChunkType.IHDR: destructify.StructureField(PngChunk_IHDR, length='length'),
            ChunkType.IEND: destructify.ConstantField(b""),
            ChunkType.TEXT: destructify.StructureField(PngChunk_tEXt, length='length'),
            ChunkType.PHYS: destructify.StructureField(PngChunk_pHYs, length='length'),
            ChunkType.PLTE: destructify.StructureField(PngChunk_PLTE, length='length'),
        },
        switch="chunk_type",
        other=destructify.FixedLengthField("length")
    )
    crc = destructify.IntegerField(4, "big", override=lambda f, v: calculate_crc(f))

    class Meta:
        capture_raw = True
        checks = [
            lambda f: f._context.fields['chunk_data'].length == f.length,
            lambda f: calculate_crc(f) == f.crc,
        ]


class PngFile(destructify.Structure):
    magic = destructify.ConstantField(b"\x89PNG\r\n\x1a\n")
    chunks = destructify.ArrayField(destructify.StructureField(PngChunk), length=-1,
                                    until=lambda c, v: v.chunk_type == "IEND")

    class Meta:
        checks = [
            lambda f: f.chunks[0].chunk_type == ChunkType.IHDR,
            lambda f: f.chunks[-1].chunk_type == ChunkType.IEND,
        ]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()

    with open(args.input, "rb") as f:
        destructify.gui.show(PngFile, f)


if __name__ == "__main__":
    main()
