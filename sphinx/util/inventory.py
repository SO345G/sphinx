"""Inventory utility functions for Sphinx."""
import os
import re
import zlib
from os import path
from typing import IO, TYPE_CHECKING, Callable, Iterator, List, Optional, Tuple

from docutils import nodes
from docutils.nodes import Element, TextElement
from docutils.utils import relative_path

from sphinx.addnodes import pending_xref
from sphinx.locale import _
from sphinx.util import logging
from sphinx.util.nodes import find_pending_xref_condition
from sphinx.util.typing import Inventory, InventoryItem

BUFSIZE = 16 * 1024
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment


class InventoryFileReader:
    """A file reader for an inventory file.

    This reader supports mixture of texts and compressed texts.
    """

    def __init__(self, stream: IO) -> None:
        self.stream = stream
        self.buffer = b''
        self.eof = False

    def read_buffer(self) -> None:
        chunk = self.stream.read(BUFSIZE)
        if chunk == b'':
            self.eof = True
        self.buffer += chunk

    def readline(self) -> str:
        pos = self.buffer.find(b'\n')
        if pos != -1:
            line = self.buffer[:pos].decode()
            self.buffer = self.buffer[pos + 1:]
        elif self.eof:
            line = self.buffer.decode()
            self.buffer = b''
        else:
            self.read_buffer()
            line = self.readline()

        return line

    def readlines(self) -> Iterator[str]:
        while not self.eof:
            line = self.readline()
            if line:
                yield line

    def read_compressed_chunks(self) -> Iterator[bytes]:
        decompressor = zlib.decompressobj()
        while not self.eof:
            self.read_buffer()
            yield decompressor.decompress(self.buffer)
            self.buffer = b''
        yield decompressor.flush()

    def read_compressed_lines(self) -> Iterator[str]:
        buf = b''
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b'\n')
            while pos != -1:
                yield buf[:pos].decode()
                buf = buf[pos + 1:]
                pos = buf.find(b'\n')


class InventoryFile:
    @classmethod
    def load(cls, stream: IO, uri: str, joinfunc: Callable) -> Inventory:
        reader = InventoryFileReader(stream)
        line = reader.readline().rstrip()
        if line == '# Sphinx inventory version 1':
            return cls.load_v1(reader, uri, joinfunc)
        elif line == '# Sphinx inventory version 2':
            return cls.load_v2(reader, uri, joinfunc)
        else:
            raise ValueError('invalid inventory header: %s' % line)

    @classmethod
    def load_v1(cls, stream: InventoryFileReader, uri: str, join: Callable) -> Inventory:
        invdata: Inventory = {}
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]
        for line in stream.readlines():
            name, type, location = line.rstrip().split(None, 2)
            location = join(uri, location)
            # version 1 did not add anchors to the location
            if type == 'mod':
                type = 'py:module'
                location += '#module-' + name
            else:
                type = 'py:' + type
                location += '#' + name
            invdata.setdefault(type, {})[name] = (projname, version, location, '-')
        return invdata

    @classmethod
    def load_v2(cls, stream: InventoryFileReader, uri: str, join: Callable) -> Inventory:
        invdata: Inventory = {}
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]
        line = stream.readline()
        if 'zlib' not in line:
            raise ValueError('invalid inventory header (not compressed): %s' % line)

        for line in stream.read_compressed_lines():
            # be careful to handle names with embedded spaces correctly
            m = re.match(r'(?x)(.+?)\s+(\S+)\s+(-?\d+)\s+?(\S*)\s+(.*)',
                         line.rstrip())
            if not m:
                continue
            name, type, prio, location, dispname = m.groups()
            if ':' not in type:
                # wrong type value. type should be in the form of "{domain}:{objtype}"
                #
                # Note: To avoid the regex DoS, this is implemented in python (refs: #8175)
                continue
            if type == 'py:module' and type in invdata and name in invdata[type]:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue
            if location.endswith('$'):
                location = location[:-1] + name
            location = join(uri, location)
            invdata.setdefault(type, {})[name] = (projname, version,
                                                  location, dispname)
        return invdata

    @classmethod
    def dump(cls, filename: str, env: "BuildEnvironment", builder: "Builder") -> None:
        def escape(string: str) -> str:
            return re.sub("\\s+", " ", string)

        with open(os.path.join(filename), 'wb') as f:
            # header
            f.write(('# Sphinx inventory version 2\n'
                     '# Project: %s\n'
                     '# Version: %s\n'
                     '# The remainder of this file is compressed using zlib.\n' %
                     (escape(env.config.project),
                      escape(env.config.version))).encode())

            # body
            compressor = zlib.compressobj(9)
            for domainname, domain in sorted(env.domains.items()):
                for name, dispname, typ, docname, anchor, prio in \
                        sorted(domain.get_objects()):
                    if anchor.endswith(name):
                        # this can shorten the inventory by as much as 25%
                        anchor = anchor[:-len(name)] + '$'
                    uri = builder.get_target_uri(docname)
                    if anchor:
                        uri += '#' + anchor
                    if dispname == name:
                        dispname = '-'
                    entry = ('%s %s:%s %s %s %s\n' %
                             (name, domainname, typ, prio, uri, dispname))
                    f.write(compressor.compress(entry.encode()))
            f.write(compressor.flush())


class InventoryItemSet:
    def __init__(self):
        self._items = []  # type: List[Tuple[str, InventoryItem]]

    def __str__(self) -> str:
        return "InventoryItemSet({})".format(", ".join(str(e) for e in self._items))

    def __repr__(self) -> str:
        return str(self)

    def append(self, item: Tuple[str, InventoryItem]) -> None:
        self._items.append(item)

    def select_inventory(self, inv_name: Optional[str]) -> "InventoryItemSet":
        if inv_name is None:
            return self
        items = [item for item in self._items if item[0] == inv_name]
        if len(items) == 0:
            return None
        else:
            res = InventoryItemSet()
            res._items = items
            return res

    def make_refnode(self, domain_name: str, node: pending_xref,
                     contnode: TextElement) -> Element:
        assert len(self._items) != 0
        namedRes = [r for r in self._items if r[0] is not None]
        unnamedRes = [r for r in self._items if r[0] is None]
        assert len(unnamedRes) <= 1
        if len(unnamedRes) != 0:
            r = unnamedRes[0]
        else:
            r = min(namedRes, key=lambda r: r[0])

        # determine the contnode by pending_xref_condition
        content = find_pending_xref_condition(node, 'resolved')
        if content:
            # resolved condition found.
            contnodes = content.children
            contnode = content.children[0]  # type: ignore
        else:
            # not resolved. Use the given contnode
            contnodes = [contnode]

        inv_name, inner_data = r

        proj, version, uri, dispname = inner_data
        if '://' not in uri and node.get('refdoc'):
            # get correct path in case of subdirectories
            uri = path.join(relative_path(node['refdoc'], '.'), uri)
        if version:
            reftitle = _('(in %s v%s)') % (proj, version)
        else:
            reftitle = _('(in %s)') % (proj,)
        newnode = nodes.reference('', '', internal=False, refuri=uri, reftitle=reftitle)
        if node.get('refexplicit'):
            # use whatever title was given
            newnode.extend(contnodes)
        elif dispname == '-' or \
                (domain_name == 'std' and node['reftype'] == 'keyword'):
            # use whatever title was given, but strip prefix
            title = contnode.astext()
            if node.get('origtarget') and \
                    node['origtarget'] != node['reftarget'] and \
                    title.startswith(inv_name + ':'):
                newnode.append(contnode.__class__(title[len(inv_name) + 1:],
                                                  title[len(inv_name) + 1:]))
            else:
                newnode.extend(contnodes)
        else:
            # else use the given display name (used for :ref:)
            newnode.append(contnode.__class__(dispname, dispname))
        return newnode
