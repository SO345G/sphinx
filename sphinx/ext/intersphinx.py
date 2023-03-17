"""Insert links to objects documented in remote Sphinx documentation.

This works as follows:

* Each Sphinx HTML build creates a file named "objects.inv" that contains a
  mapping from object names to URIs relative to the HTML set's root.

* Projects using the Intersphinx extension can specify links to such mapping
  files in the `intersphinx_mapping` config value.  The mapping will then be
  used to resolve otherwise missing references to objects into links to the
  other documentation.

* By default, the mapping file is assumed to be at the same location as the
  rest of the documentation; however, the location of the mapping file can
  also be specified individually, e.g. if the docs should be buildable
  without Internet access.
"""

from __future__ import annotations

import concurrent.futures
import copy
import functools
import posixpath
import re
import sys
import time
from os import path
from typing import IO, TYPE_CHECKING, Any, cast
from urllib.parse import urlsplit, urlunsplit

from docutils import nodes

import sphinx
from sphinx.addnodes import pending_xref
from sphinx.builders.html import INVENTORY_FILENAME
from sphinx.errors import ExtensionError
from sphinx.locale import __
from sphinx.transforms.post_transforms import ReferencesResolver
from sphinx.util import logging, requests
from sphinx.util.docutils import CustomReSTDispatcher, SphinxRole
from sphinx.util.inventory import InventoryFile, InventoryItemSet

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Tuple, Union

    from docutils.nodes import Node, TextElement, system_message
    from docutils.utils import Reporter

    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.domains import Domain
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import Inventory, RoleFunction

    InventoryCacheEntry = Tuple[Union[str, None], int, Inventory]

logger = logging.getLogger(__name__)


def _initialise_environment_for_intersphinx(env: BuildEnvironment) -> None:
    if not hasattr(env, 'intersphinx_cache'):
        _process_disabled_reftypes(env)

        # initial storage when fetching inventories before processing
        env.intersphinx_cache = {}  # type: ignore[attr-defined]
        # list of inventory names for validation
        env.intersphinx_inventory_names = set()  # type: ignore[attr-defined]
        # old stuff
        env.intersphinx_inventory = {}  # type: ignore[attr-defined]
        # store inventory data in domain-specific data structures
        env.intersphinx_by_domain_inventory = {}  # type: ignore[attr-defined]
        _reinitialise_inventories(env)


def _process_disabled_reftypes(env: BuildEnvironment) -> None:
    # is a separate function so the tests can use it
    env.intersphinx_all_objtypes_disabled = False  # type: ignore[attr-defined]
    env.intersphinx_all_domain_objtypes_disabled = set()  # type: ignore[attr-defined]
    env.intersphinx_disabled_per_domain = {}  # type: ignore[attr-defined]
    for d in env.config.intersphinx_disabled_reftypes:
        if d == '*':
            env.intersphinx_all_objtypes_disabled = True  # type: ignore[attr-defined]
        elif ':' in d:
            domain, typ = d.split(':', 1)
            if typ == '*':
                env.intersphinx_all_domain_objtypes_disabled.add(domain)  # type: ignore[attr-defined]
            else:
                env.intersphinx_disabled_per_domain.setdefault(  # type: ignore[attr-defined]
                    domain, []).append(typ)


def _reinitialise_inventories(env: BuildEnvironment) -> None:
    env.intersphinx_inventory_names.clear()  # type: ignore[attr-defined]
    env.intersphinx_inventory.clear()  # type: ignore[attr-defined]
    env.intersphinx_by_domain_inventory.clear()  # type: ignore[attr-defined]

    # reinitialise the domain-specific inventory stores
    for domain in env.domains.values():
        inv = copy.deepcopy(domain.initial_intersphinx_inventory)
        env.intersphinx_by_domain_inventory[domain.name] = inv  # type: ignore[attr-defined]


class _EnvAdapter:
    """Adapter for environment to set inventory data and configuration settings."""

    def __init__(self, env: BuildEnvironment) -> None:
        self.env = env
        _initialise_environment_for_intersphinx(env)

    @property
    def all_objtypes_disabled(self) -> bool:
        return self.env.intersphinx_all_objtypes_disabled    # type: ignore

    def all_domain_objtypes_disabled(self, domain: str) -> bool:
        return domain in self.env.intersphinx_all_domain_objtypes_disabled  # type: ignore

    def disabled_objtypes_in_domain(self, domain: str) -> list[str]:
        return self.env.intersphinx_disabled_per_domain.get(domain, [])  # type: ignore

    @property
    def cache(self) -> dict[str, InventoryCacheEntry]:
        """Intersphinx cache.

        - Key is the URI of the remote inventory
        - Element one is the key given in the Sphinx intersphinx_mapping
          configuration value
        - Element two is a time value for cache invalidation, a float
        - Element three is the loaded remote inventory, type Inventory
        """
        return self.env.intersphinx_cache  # type: ignore

    @property
    def main_inventory(self) -> Inventory:
        # old stuff
        return self.env.intersphinx_inventory  # type: ignore

    @property
    def names(self) -> set[str | None]:
        return self.env.intersphinx_inventory_names  # type: ignore

    @property
    def by_domain_inventory(self) -> dict[str, dict[str, Any]]:
        return self.env.intersphinx_by_domain_inventory  # type: ignore

    def clear(self) -> None:
        _reinitialise_inventories(self.env)


def _strip_basic_auth(url: str) -> str:
    """Returns *url* with basic auth credentials removed. Also returns the
    basic auth username and password if they're present in *url*.

    E.g.: https://user:pass@example.com => https://example.com

    *url* need not include basic auth credentials.

    :param url: url which may or may not contain basic auth credentials
    :type url: ``str``

    :return: *url* with any basic auth creds removed
    :rtype: ``str``
    """
    frags = list(urlsplit(url))
    # swap out "user[:pass]@hostname" for "hostname"
    if '@' in frags[1]:
        frags[1] = frags[1].split('@')[1]
    return urlunsplit(frags)


def _read_from_url(url: str, config: Config | None = None) -> IO:
    """Reads data from *url* with an HTTP *GET*.

    This function supports fetching from resources which use basic HTTP auth as
    laid out by RFC1738 § 3.1. See § 5 for grammar definitions for URLs.

    .. seealso:

       https://www.ietf.org/rfc/rfc1738.txt

    :param url: URL of an HTTP resource
    :type url: ``str``

    :return: data read from resource described by *url*
    :rtype: ``file``-like object
    """
    r = requests.get(url, stream=True, config=config, timeout=config.intersphinx_timeout)
    r.raise_for_status()
    r.raw.url = r.url
    # decode content-body based on the header.
    # ref: https://github.com/kennethreitz/requests/issues/2155
    r.raw.read = functools.partial(r.raw.read, decode_content=True)
    return r.raw


def _get_safe_url(url: str) -> str:
    """Gets version of *url* with basic auth passwords obscured. This function
    returns results suitable for printing and logging.

    E.g.: https://user:12345@example.com => https://user@example.com

    :param url: a url
    :type url: ``str``

    :return: *url* with password removed
    :rtype: ``str``
    """
    parts = urlsplit(url)
    if parts.username is None:
        return url
    else:
        frags = list(parts)
        if parts.port:
            frags[1] = f'{parts.username}@{parts.hostname}:{parts.port}'
        else:
            frags[1] = f'{parts.username}@{parts.hostname}'

        return urlunsplit(frags)


def fetch_inventory(app: Sphinx, uri: str, inv: str) -> Inventory:
    """Fetch, parse and return an intersphinx inventory file."""
    # both *uri* (base URI of the links to generate) and *inv* (actual
    # location of the inventory file) can be local or remote URIs
    localuri = '://' not in uri
    if not localuri:
        # case: inv URI points to remote resource; strip any existing auth
        uri = _strip_basic_auth(uri)
    try:
        if '://' in inv:
            f = _read_from_url(inv, config=app.config)
        else:
            f = open(path.join(app.srcdir, inv), 'rb')
    except Exception as err:
        err.args = ('intersphinx inventory %r not fetchable due to %s: %s',
                    inv, err.__class__, str(err))
        raise
    try:
        if hasattr(f, 'url'):
            newinv = f.url
            if inv != newinv:
                logger.info(__('intersphinx inventory has moved: %s -> %s'), inv, newinv)

                if uri in (inv, path.dirname(inv), path.dirname(inv) + '/'):
                    uri = path.dirname(newinv)
        with f:
            try:
                join = path.join if localuri else posixpath.join
                invdata = InventoryFile.load(f, uri, join)
            except ValueError as exc:
                raise ValueError('unknown or unsupported inventory version: %r' % exc) from exc
    except Exception as err:
        err.args = ('intersphinx inventory %r not readable due to %s: %s',
                    inv, err.__class__.__name__, str(err))
        raise
    else:
        return invdata


def fetch_inventory_group(
    name: str | None,
    uri: str,
    invs: tuple[str | None, ...],
    cache: dict[str, InventoryCacheEntry],
    app: Sphinx,
    now: int,
) -> bool:
    cache_time = now - app.config.intersphinx_cache_limit * 86400
    failures = []
    try:
        for inv in invs:
            if not inv:
                inv = posixpath.join(uri, INVENTORY_FILENAME)
            # decide whether the inventory must be read: always read local
            # files; remote ones only if the cache time is expired
            if '://' not in inv or uri not in cache or cache[uri][1] < cache_time:
                safe_inv_url = _get_safe_url(inv)
                logger.info(__('loading intersphinx inventory from %s...'), safe_inv_url)
                try:
                    invdata = fetch_inventory(app, uri, inv)
                except Exception as err:
                    failures.append(err.args)
                    continue
                if invdata:
                    cache[uri] = name, now, invdata
                    return True
        return False
    finally:
        if failures == []:
            pass
        elif len(failures) < len(invs):
            logger.info(__("encountered some issues with some of the inventories,"
                           " but they had working alternatives:"))
            for fail in failures:
                logger.info(*fail)
        else:
            issues = '\n'.join([f[0] % f[1:] for f in failures])
            logger.warning(__("failed to reach any of the inventories "
                              "with the following issues:") + "\n" + issues)


debug = False


def load_mappings(app: Sphinx) -> None:
    """Load all intersphinx mappings into the environment."""
    env = app.builder.env

    now = int(time.time())
    _initialise_environment_for_intersphinx(env)
    intersphinx_cache: dict[str, InventoryCacheEntry]
    intersphinx_cache = env.intersphinx_cache  # type: ignore[attr-defined]

    with concurrent.futures.ThreadPoolExecutor() as pool:
        futures = []
        name: str | None
        uri: str
        invs: tuple[str | None, ...]
        for name, (uri, invs) in app.config.intersphinx_mapping.values():
            futures.append(pool.submit(
                fetch_inventory_group, name, uri, invs, intersphinx_cache, app, now,
            ))
        updated = [f.result() for f in concurrent.futures.as_completed(futures)]

    if any(updated):
        _reinitialise_inventories(env)
        inventory_names = env.intersphinx_inventory_names  # type: ignore[attr-defined]

        if True:
            # old stuff, still used in the tests
            named_vals = []
            unnamed_vals = []
            for name, _expiry, invdata in intersphinx_cache.values():
                if name:
                    named_vals.append((name, invdata))
                else:
                    unnamed_vals.append((name, invdata))
            for _name, invdata in sorted(named_vals) + unnamed_vals:
                for type, objects in invdata.items():
                    env.intersphinx_inventory.setdefault(type, {}).update(objects)  # type: ignore[attr-defined]
            # end of old stuff

        # first collect all entries indexed by domain, object name, and object type
        # domain -> object_type -> object_name -> InventoryItemSet([(inv_name, inner_data)])
        entries: dict[str, dict[str, dict[str, InventoryItemSet]]] = {}
        for inv_name, _, inv_data in intersphinx_cache.values():
            assert inv_name not in inventory_names
            inventory_names.add(inv_name)

            for inv_object_type, inv_objects in inv_data.items():
                domain_name, object_type = inv_object_type.split(':')

                # skip objects in domains we don't use
                if domain_name not in app.env.domains:
                    continue

                domain_entries = entries.setdefault(domain_name, {})
                per_type = domain_entries.setdefault(object_type, {})
                for object_name, object_data in inv_objects.items():
                    item_set = per_type.setdefault(object_name, InventoryItemSet())
                    item_set.append(inv_name, object_data)

        # and then give the data to each domain
        for domain_name, domain_entries in entries.items():
            if debug:
                print(f"intersphinx debug(load_mappings): domain={domain_name}")
                print(f"intersphinx debug(load_mappings): entries={domain_entries}")
            domain = app.env.domains[domain_name]
            domain_store = env.intersphinx_by_domain_inventory[domain_name]  # type: ignore[attr-defined]
            domain.intersphinx_add_entries(domain_store, domain_entries)


def _resolve_reference_in_domain(env: BuildEnvironment,
                                 inv_name: str | None,
                                 honor_disabled_refs: bool,
                                 domain: Domain,
                                 node: pending_xref, contnode: TextElement,
                                 ) -> nodes.reference | None:
    if honor_disabled_refs:
        assert not env.intersphinx_all_objtypes_disabled  # type: ignore[attr-defined]
        assert domain.name not in env.intersphinx_all_domain_objtypes_disabled  # type: ignore[attr-defined]
        disabled_refs = env.intersphinx_disabled_per_domain.get(domain.name, [])  # type: ignore[attr-defined]
    else:
        disabled_refs = []

    domain_store = env.intersphinx_by_domain_inventory[domain.name]  # type: ignore[attr-defined]
    inv_set = domain.intersphinx_resolve_xref(
        env, domain_store, node['reftype'], node['reftarget'], disabled_refs, node, contnode)
    if debug:
        print(f"intersphinx debug(_resolve_reference_in_domain): inv_set={inv_set}")
    if inv_set is None:
        return None
    inv_set_restricted = inv_set.select_inventory(inv_name)
    if debug:
        print("intersphinx debug(_resolve_reference_in_domain):"
              " inv_name={}, inv_set_restricted={}".format(inv_name, inv_set_restricted))
    try:
        return inv_set_restricted.make_reference_node(domain.name, node, contnode)
    except ValueError:
        return None


def _resolve_reference(env: BuildEnvironment, inv_name: str | None,
                       honor_disabled_refs: bool,
                       node: pending_xref, contnode: TextElement) -> nodes.reference | None:
    # disabling should only be done if no inventory is given
    honor_disabled_refs = honor_disabled_refs and inv_name is None

    if honor_disabled_refs and env.intersphinx_all_objtypes_disabled:  # type: ignore[attr-defined]
        return None

    if node['reftype'] == 'any':
        for domain_name, domain in env.domains.items():
            if (honor_disabled_refs
                    and domain_name in env.intersphinx_all_domain_objtypes_disabled):  # type: ignore[attr-defined]
                continue
            res = _resolve_reference_in_domain(env, inv_name, honor_disabled_refs,
                                               domain, node, contnode)
            if res is not None:
                return res
        return None
    else:
        domain_name = node.get('refdomain')
        if not domain_name:
            # only objects in domains are in the inventory
            return None
        if honor_disabled_refs and domain_name in env.intersphinx_all_domain_objtypes_disabled:  # type: ignore[attr-defined]
            return None
        domain = env.get_domain(domain_name)
        return _resolve_reference_in_domain(env, inv_name, honor_disabled_refs,
                                            domain, node, contnode)


def _inventory_exists(env: BuildEnvironment, inv_name: str) -> bool:
    return inv_name in env.intersphinx_inventory_names  # type: ignore[attr-defined]


def _resolve_reference_in_inventory(env: BuildEnvironment,
                                    inv_name: str,
                                    node: pending_xref, contnode: TextElement,
                                    ) -> nodes.reference | None:
    """Attempt to resolve a missing reference via intersphinx references.

    Resolution is tried in the given inventory with the target as is.

    Requires ``_inventory_exists(env, inv_name)``.
    """
    assert _inventory_exists(env, inv_name)
    return _resolve_reference(env, inv_name, False, node, contnode)


def _resolve_reference_any_inventory(env: BuildEnvironment,
                                     honor_disabled_refs: bool,
                                     node: pending_xref, contnode: TextElement,
                                     ) -> nodes.reference | None:
    """Attempt to resolve a missing reference via intersphinx references.

    Resolution is tried with the target as is in any inventory.
    """
    return _resolve_reference(env, None, honor_disabled_refs, node, contnode)


def _resolve_reference_detect_inventory(env: BuildEnvironment,
                                        node: pending_xref, contnode: TextElement,
                                        ) -> nodes.reference | None:
    """Attempt to resolve a missing reference via intersphinx references.

    Resolution is tried first with the target as is in any inventory.
    If this does not succeed, then the target is split by the first ``:``,
    to form ``inv_name:newtarget``. If ``inv_name`` is a named inventory, then resolution
    is tried in that inventory with the new target.
    """

    # ordinary direct lookup, use data as is
    res = _resolve_reference_any_inventory(env, True, node, contnode)
    if res is not None:
        return res

    # try splitting the target into 'inv_name:target'
    target = node['reftarget']
    if ':' not in target:
        return None
    inv_name, newtarget = target.split(':', 1)
    if not _inventory_exists(env, inv_name):
        return None
    node['reftarget'] = newtarget
    node['origtarget'] = target
    res_inv = _resolve_reference_in_inventory(env, inv_name, node, contnode)
    node['reftarget'] = target
    del node['origtarget']
    return res_inv


def _missing_reference(app: Sphinx, env: BuildEnvironment, node: pending_xref,
                       contnode: TextElement) -> nodes.reference | None:
    """Attempt to resolve a missing reference via intersphinx references."""

    return _resolve_reference_detect_inventory(env, node, contnode)


class IntersphinxDispatcher(CustomReSTDispatcher):
    """Custom dispatcher for external role.

    This enables :external:***:/:external+***: roles on parsing reST document.
    """

    def role(
        self, role_name: str, language_module: ModuleType, lineno: int, reporter: Reporter,
    ) -> tuple[RoleFunction, list[system_message]]:
        if len(role_name) > 9 and role_name.startswith(('external:', 'external+')):
            return IntersphinxRole(role_name), []
        else:
            return super().role(role_name, language_module, lineno, reporter)


class IntersphinxRole(SphinxRole):
    # group 1: just for the optionality of the inventory name
    # group 2: the inventory name (optional)
    # group 3: the domain:role or role part
    _re_inv_ref = re.compile(r"(\+([^:]+))?:(.*)")

    def __init__(self, orig_name: str) -> None:
        self.orig_name = orig_name

    def run(self) -> tuple[list[Node], list[system_message]]:
        assert self.name == self.orig_name.lower()
        inventory, name_suffix = self.get_inventory_and_name_suffix(self.orig_name)
        if inventory and not _inventory_exists(self.env, inventory):
            logger.warning(__('inventory for external cross-reference not found: %s'),
                           inventory, location=(self.env.docname, self.lineno))
            return [], []

        role_name = self.get_role_name(name_suffix)
        if role_name is None:
            logger.warning(__('role for external cross-reference not found: %s'), name_suffix,
                           location=(self.env.docname, self.lineno))
            return [], []

        result, messages = self.invoke_role(role_name)
        for node in result:
            if isinstance(node, pending_xref):
                node['intersphinx'] = True
                node['inventory'] = inventory

        return result, messages

    def get_inventory_and_name_suffix(self, name: str) -> tuple[str | None, str]:
        assert name.startswith('external'), name
        assert name[8] in ':+', name
        # either we have an explicit inventory name, i.e,
        # :external+inv:role:        or
        # :external+inv:domain:role:
        # or we look in all inventories, i.e.,
        # :external:role:            or
        # :external:domain:role:
        inv, suffix = IntersphinxRole._re_inv_ref.fullmatch(name, 8).group(2, 3)
        return inv, suffix

    def get_role_name(self, name: str) -> tuple[str, str] | None:
        names = name.split(':')
        if len(names) == 1:
            # role
            default_domain = self.env.temp_data.get('default_domain')
            domain = default_domain.name if default_domain else None
            role = names[0]
        elif len(names) == 2:
            # domain:role:
            domain = names[0]
            role = names[1]
        else:
            return None

        if domain and self.is_existent_role(domain, role):
            return (domain, role)
        elif self.is_existent_role('std', role):
            return ('std', role)
        else:
            return None

    def is_existent_role(self, domain_name: str, role_name: str) -> bool:
        try:
            domain = self.env.get_domain(domain_name)
            return role_name in domain.roles
        except ExtensionError:
            return False

    def invoke_role(self, role: tuple[str, str]) -> tuple[list[Node], list[system_message]]:
        domain = self.env.get_domain(role[0])
        if domain:
            role_func = domain.role(role[1])

            return role_func(':'.join(role), self.rawtext, self.text, self.lineno,
                             self.inliner, self.options, self.content)
        else:
            return [], []


class IntersphinxRoleResolver(ReferencesResolver):
    """pending_xref node resolver for intersphinx role.

    This resolves pending_xref nodes generated by :intersphinx:***: role.
    """

    default_priority = ReferencesResolver.default_priority - 1

    def run(self, **kwargs: Any) -> None:
        for node in self.document.findall(pending_xref):
            if 'intersphinx' not in node:
                continue
            contnode = cast(nodes.TextElement, node[0].deepcopy())
            inv_name = node['inventory']
            if inv_name is not None:
                assert _inventory_exists(self.env, inv_name)
                newnode = _resolve_reference_in_inventory(self.env, inv_name, node, contnode)
            else:
                newnode = _resolve_reference_any_inventory(self.env, False, node, contnode)
            if newnode is None:
                typ = node['reftype']
                msg = (__('external %s:%s reference target not found: %s') %
                       (node['refdomain'], typ, node['reftarget']))
                logger.warning(msg, location=node, type='ref', subtype=typ)
                node.replace_self(contnode)
            else:
                node.replace_self(newnode)


def install_dispatcher(app: Sphinx, docname: str, source: list[str]) -> None:
    """Enable IntersphinxDispatcher.

    .. note:: The installed dispatcher will be uninstalled on disabling sphinx_domain
              automatically.
    """
    dispatcher = IntersphinxDispatcher()
    dispatcher.enable()


def normalize_intersphinx_mapping(app: Sphinx, config: Config) -> None:
    for key, value in config.intersphinx_mapping.copy().items():
        try:
            if isinstance(value, (list, tuple)):
                # new format
                name, (uri, inv) = key, value
                if not isinstance(name, str):
                    logger.warning(__('intersphinx identifier %r is not string. Ignored'),
                                   name)
                    config.intersphinx_mapping.pop(key)
                    continue
            else:
                # old format, no name
                # xref RemovedInSphinx80Warning
                name, uri, inv = None, key, value
                msg = (
                    "The pre-Sphinx 1.0 'intersphinx_mapping' format is "
                    "deprecated and will be removed in Sphinx 8. Update to the "
                    "current format as described in the documentation. "
                    f"Hint: \"intersphinx_mapping = {{'<name>': {(uri, inv)!r}}}\"."
                    "https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#confval-intersphinx_mapping"  # NoQA: E501
                )
                logger.warning(msg)

            if not isinstance(inv, tuple):
                config.intersphinx_mapping[key] = (name, (uri, (inv,)))
            else:
                config.intersphinx_mapping[key] = (name, (uri, inv))
        except Exception as exc:
            logger.warning(__('Failed to read intersphinx_mapping[%s], ignored: %r'), key, exc)
            config.intersphinx_mapping.pop(key)


# deprecated name -> (object to return, removal version, canonical path or empty string)
_DEPRECATED_OBJECTS = {
    'InventoryAdapter': (_EnvAdapter, (8, 0), 'sphinx.ext.intersphinx._EnvAdapter'),
    'resolve_reference_in_inventory': (_resolve_reference_in_inventory, (8, 0), 'sphinx.ext.intersphinx._resolve_reference_in_inventory'),
}


def __getattr__(name):
    if name not in _DEPRECATED_OBJECTS:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')

    from sphinx.deprecation import _deprecation_warning

    deprecated_object, removal, canonical_name = _DEPRECATED_OBJECTS[name]
    _deprecation_warning(__name__, name, canonical_name, remove=removal)
    return deprecated_object


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_config_value('intersphinx_mapping', {}, True)
    app.add_config_value('intersphinx_cache_limit', 5, False)
    app.add_config_value('intersphinx_timeout', None, False)
    app.add_config_value('intersphinx_disabled_reftypes', ['std:doc'], True)
    app.connect('config-inited', normalize_intersphinx_mapping, priority=800)
    app.connect('builder-inited', load_mappings)
    app.connect('source-read', install_dispatcher)
    app.connect('missing-reference', _missing_reference)
    app.add_post_transform(IntersphinxRoleResolver)
    return {
        'version': sphinx.__display_version__,
        'env_version': 2,
        'parallel_read_safe': True,
    }


def inspect_main(argv: list[str]) -> None:
    """Debug functionality to print out an inventory"""
    if len(argv) < 1:
        print("Print out an inventory file.\n"
              "Error: must specify local path or URL to an inventory file.",
              file=sys.stderr)
        raise SystemExit(1)

    class MockConfig:
        intersphinx_timeout: int | None = None
        tls_verify = False
        user_agent = None

    class MockApp:
        srcdir = ''
        config = MockConfig()

        def warn(self, msg: str) -> None:
            print(msg, file=sys.stderr)

    try:
        filename = argv[0]
        invdata = fetch_inventory(MockApp(), '', filename)  # type: ignore
        for key in sorted(invdata or {}):
            print(key)
            for entry, einfo in sorted(invdata[key].items()):
                print('\t%-40s %s%s' % (entry,
                                        '%-40s: ' % einfo[3] if einfo[3] != '-' else '',
                                        einfo[2]))
    except ValueError as exc:
        print(exc.args[0] % exc.args[1:])
    except Exception as exc:
        print('Unknown error: %r' % exc)


if __name__ == '__main__':
    import logging as _logging
    _logging.basicConfig()

    inspect_main(argv=sys.argv[1:])
