from __future__ import annotations

import re
import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import io
    import os

try:
    import PIL.Image
except ImportError:
    def _get_image_size_pil(filename: str, /) -> tuple[int, int] | None:
        return None
else:
    def _get_image_size_pil(filename: str, /) -> tuple[int, int] | None:
        try:
            with PIL.Image.open(filename) as im:
                return im.size
        except Exception:
            return None


def get_image_size(filename: str) -> tuple[int, int] | None:
    try:
        width, height = _get_image_size(filename)
    except ValueError:
        return None

    if width == -1:
        return _get_image_size_pil(filename)  # fallback to Pillow
    return width, height


def _get_image_size(path: os.PathLike | str) -> tuple[int, int]:
    """Return (width, height) for a given img file content."""

    with open(path, "rb") as file:
        head = file.read(24)
        size = len(head)

        # handle GIFs
        if head.startswith((b'GIF87a', b'GIF89a')):
            return _gif(head, size)

        # handle PNGs
        if head.startswith(b'\211PNG\r\n\032\n'):
            return _png(head, size)

        # handle JPEGs
        if head.startswith(b'\377\330'):
            try:
                file.seek(0)  # Read 0xff next
                size = 2
                ftype = 0
                while not 0xc0 <= ftype <= 0xcf or ftype in [0xc4, 0xc8, 0xcc]:
                    file.seek(size, 1)
                    byte = file.read(1)
                    while ord(byte) == 0xff:
                        byte = file.read(1)
                    ftype = ord(byte)
                    size = struct.unpack('>H', file.read(2))[0] - 2
                # We are at a SOFn block
                file.seek(1, 1)  # Skip `precision' byte.
                height, width = struct.unpack('>HH', file.read(4))
            except (struct.error, TypeError):
                raise ValueError("Invalid JPEG file")

        # handle JPEG2000s
        if size >= 12 and head.startswith(b'\x00\x00\x00\x0cjP  \r\n\x87\n'):
            file.seek(48)
            return _jpeg2000(file.read(8))

        # handle big endian TIFF
        if size >= 8 and head.startswith(b"\x4d\x4d\x00\x2a"):
            offset = struct.unpack('>L', head[4:8])[0]
            file.seek(offset)
            ifdsize = struct.unpack(">H", file.read(2))[0]
            for _ in range(ifdsize):
                tag, datatype, count, data = struct.unpack(">HHLL", file.read(12))
                if tag == 256:
                    if datatype == 3:
                        width = int(data / 65536)
                    elif datatype == 4:
                        width = data
                    else:
                        msg = "Invalid TIFF file: width column data type should be SHORT/LONG."
                        raise ValueError(msg)
                elif tag == 257:
                    if datatype == 3:
                        height = int(data / 2**16)
                    elif datatype == 4:
                        height = data
                    else:
                        msg = ("Invalid TIFF file: "
                               "height column data type should be SHORT/LONG.")
                        raise ValueError(msg)
                if width != -1 and height != -1:
                    break
            if width == -1 or height == -1:
                msg = ("Invalid TIFF file: "
                       "width and/or height IDS entries are missing.")
                raise ValueError(msg)
            return width, height

        # handle big endian TIFF
        if head.startswith(b"\x49\x49\x2a\x00"):
            offset = struct.unpack('<L', head[4:8])[0]
            file.seek(offset)
            ifd_size = struct.unpack("<H", file.read(2))[0]
            for _ in range(ifd_size):
                tag, datatype, count, data = struct.unpack("<HHLL", file.read(12))
                if tag == 256:
                    width = data
                elif tag == 257:
                    height = data
                if width != -1 and height != -1:
                    break
            if width == -1 or height == -1:
                msg = "Invalid TIFF file: width and/or height IDS entries are missing."
                raise ValueError(msg)
            return width, height

        # handle little endian BigTiff
        elif head.startswith(b"\x49\x49\x2b\x00"):
            bytesize_offset = struct.unpack('<L', head[4:8])[0]
            if bytesize_offset != 8:
                msg = ('Invalid BigTIFF file: '
                       f'Expected offset to be 8, found {bytesize_offset} instead.')
                raise ValueError(msg)
            offset = struct.unpack('<Q', head[8:16])[0]
            file.seek(offset)
            ifd_size = struct.unpack("<Q", file.read(8))[0]
            for _ in range(ifd_size):
                tag, datatype, count, data = struct.unpack("<HHQQ", file.read(20))
                if tag == 256:
                    width = data
                elif tag == 257:
                    height = data
                if width != -1 and height != -1:
                    break
            if width == -1 or height == -1:
                msg = "Invalid BigTIFF file: width and/or height IDS entries are missing."
                raise ValueError(msg)
            return width, height

        # handle SVGs
        if head.startswith((b'<?xml', b'<svg')):
            return _svg(head + file.read(992))

        if head.startswith(b'RIFF') and head[8:12] == b'WEBP':
            return _webp(head)

    return -1, -1


def _gif(head: bytes, size: int) -> tuple[int, int]:
    if size < 10:
        raise ValueError("Invalid GIF file")
    # Check to see if content_type is correct
    try:
        width, height = struct.unpack("<hh", head[6:10])
        return width, height
    except struct.error:
        raise ValueError("Invalid GIF file")


def _png(head: bytes, size: int) -> tuple[int, int]:
    if size < 24:
        raise ValueError("Invalid PNG file")
    if head[12:16] == b'IHDR':
        try:
            width, height = struct.unpack(">LL", head[16:24])
            return width, height
        except struct.error:
            raise ValueError("Invalid PNG file")
    # Check to see if we have the right content type
    try:
        width, height = struct.unpack(">LL", head[8:16])
        return width, height
    except struct.error:
        raise ValueError("Invalid PNG file")


def _jpeg(file: io.BufferedReader) -> tuple[int, int]:
    try:
        file.seek(0)  # Read 0xff next
        size = 2
        ftype = 0
        while not 0xc0 <= ftype <= 0xcf or ftype in {0xc4, 0xc8, 0xcc}:
            file.seek(size, 1)
            byte = file.read(1)
            while ord(byte) == 0xff:
                byte = file.read(1)
            ftype = ord(byte)
            size = struct.unpack('>H', file.read(2))[0] - 2
        # We are at a SOFn block
        file.seek(1, 1)  # Skip `precision' byte.
        height, width = struct.unpack('>HH', file.read(4))
        return width, height
    except (struct.error, TypeError):
        raise ValueError("Invalid JPEG file")


def _jpeg2000(data: bytes) -> tuple[int, int]:
    try:
        height, width = struct.unpack('>LL', data)
        return width, height
    except struct.error:
        raise ValueError("Invalid JPEG2000 file")


def _svg(data: bytes) -> tuple[int, int]:
    try:
        start = data.decode('utf-8')
        width = re.search(r'[^-]width="(.*?)"', start).group(1)
        height = re.search(r'[^-]height="(.*?)"', start).group(1)
    except (UnicodeDecodeError, Exception):
        raise ValueError("Invalid SVG file")
    width = int(_convert_to_px(width))
    height = int(_convert_to_px(height))
    return width, height


def _webp(head: bytes) -> tuple[int, int]:
    if head[12:16] == b"VP8 ":
        width, height = struct.unpack("<HH", head[26:30])
        return width, height
    if head[12:16] == b"VP8X":
        width = struct.unpack("<I", head[24:27] + b"\0")[0]
        height = struct.unpack("<I", head[27:30] + b"\0")[0]
        return width, height
    if head[12:16] == b"VP8L":
        b = head[21:25]
        width = (((b[1] & 63) << 8) | b[0]) + 1
        height = (((b[3] & 15) << 10) | (b[2] << 2) | ((b[1] & 192) >> 6)) + 1
        return width, height
    raise ValueError("Unsupported WebP file")


def _convert_to_px(value: str) -> float:
    matched = re.match(r"(\d+(?:\.\d+)?)?([a-z]*)$", value)
    if not matched:
        raise ValueError(f"unknown length value: {value}")

    length, unit = matched.groups()
    if unit == "":
        return float(length)
    elif unit == "cm":
        return float(length) * 96 / 2.54
    elif unit == "mm":
        return float(length) * 96 / 2.54 / 10
    elif unit == "in":
        return float(length) * 96
    elif unit in {"pc", "pt"}:
        return float(length) * 96 / 6
    elif unit == "px":
        return float(length)

    raise ValueError(f"unknown unit type: {unit}")
