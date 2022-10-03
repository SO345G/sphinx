from __future__ import annotations


from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit


def encode_uri(uri: str) -> str:
    scheme, netloc, path, query, fragment = urlsplit(uri)
    netloc = netloc.encode('idna').decode('ascii')
    path = quote_plus(path, '/')
    query = urlencode(parse_qsl(query))
    return urlunsplit((scheme, netloc, path, query, fragment))


def isurl(url: str) -> bool:
    """Check *url* is URL or not."""
    return bool(url) and '://' in url
