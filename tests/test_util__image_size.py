"""Test image size util."""

from sphinx.util._image_size import get_image_size

GIF_FILENAME = 'img.gif'
PNG_FILENAME = 'img.png'
PDF_FILENAME = 'img.pdf'
TXT_FILENAME = 'index.txt'


def test_get_image_size(rootdir):
    assert get_image_size(rootdir / 'test-root' / GIF_FILENAME) == (200, 181)
    assert get_image_size(rootdir / 'test-root' / PNG_FILENAME) == (200, 181)
    assert get_image_size(rootdir / 'test-root' / PDF_FILENAME) is None
    assert get_image_size(rootdir / 'test-root' / TXT_FILENAME) is None
