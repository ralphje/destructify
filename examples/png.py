import destructify
import enum
from binascii import crc32


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


class PhysUnit(enum.IntEnum):
    Unknown = 0
    Meter = 1


class PngChunk_pHYs(destructify.Structure):
    pixels_per_unit_x = destructify.IntegerField(4, "big")
    pixels_per_unit_y = destructify.IntegerField(4, "big")
    unit = destructify.EnumField(destructify.IntegerField(1), PhysUnit)


def check_crc(f):
    crc = 0
    crc = crc32(f._context.fields['chunk_type'].raw, crc)
    crc = crc32(f._context.fields['chunk_data'].raw, crc)
    return crc == f.crc


class PngChunk(destructify.Structure):
    length = destructify.IntegerField(4, "big")
    chunk_type = destructify.StringField(length=4, encoding="ascii")
    chunk_data = destructify.SwitchField(
        cases={
            "IHDR": destructify.StructureField(PngChunk_IHDR),
            "IEND": destructify.ConstantField(b""),
            "tEXt": destructify.StructureField(PngChunk_tEXt),
            "pHYs": destructify.StructureField(PngChunk_pHYs),
        },
        switch="chunk_type",
        other=destructify.FixedLengthField("length")
    )

    # TODO: Calculate CRC when building
    crc = destructify.IntegerField(4, "big")

    class Meta:
        capture_raw = True
        checks = [
            lambda f: f._context.fields['chunk_data'].length == f.length,
            lambda f: check_crc(f),
        ]


class PngFile(destructify.Structure):
    magic = destructify.ConstantField(b"\x89PNG\r\n\x1a\n")
    chunks = destructify.ArrayField(destructify.StructureField(PngChunk), length=-1)

    class Meta:
        checks = [
            lambda f: f.chunks[0].chunk_type == "IHDR",
            lambda f: f.chunks[-1].chunk_type == "IEND",
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
