import pytest
from docutils import nodes


@pytest.mark.sphinx('html', testroot='issue-11618')
def test_issue_11618(app):
    env = app.env

    app.builder.build_all()

    doctree = env.get_doctree('index')
    env.pyg_descinfo_tbl = pyg_descinfo_tbl = {}
    doctree.walkabout(CollectInfo(env, doctree))

    items = []
    for section in doctree:
        if isinstance(section, nodes.section):
            refid = section["ids"][0]
            descinfo = pyg_descinfo_tbl[refid.removeprefix(MODULE_ID_PREFIX)]  # A KeyError would mean a bug.
            items.append(descinfo)
            for refid in descinfo["children"]:
                items.append(pyg_descinfo_tbl[refid])  # A KeyError would mean a bug.

    assert [(item["fullname"], item["signatures"], item["summary"]) for item in items] == [
        ('pygame.key', [], 'pygame module to work with the keyboard'),
        ('pygame.key.get_focused', ['get_focused() -> bool'], 'true if the display is receiving keyboard input from the system'),
        ('pygame.key.get_pressed', ['get_pressed() -> bools'], 'get the state of all keyboard buttons'),
        ('pygame.key.get_mods', ['get_mods() -> int'], 'determine which modifier keys are being held'),
        ('pygame.key.set_mods', ['set_mods(int) -> None'], 'temporarily set which modifier keys are pressed'),
        ('pygame.key.set_repeat', ['set_repeat() -> None', 'set_repeat(delay) -> None', 'set_repeat(delay, interval) -> None'], 'control how held keys are repeated'),
        ('pygame.key.get_repeat', ['get_repeat() -> (delay, interval)'], 'see how held keys are repeated'),
        ('pygame.key.name', ['name(key, use_compat=True) -> str'], 'get the name of a key identifier'),
        ('pygame.key.key_code', ['key_code(name=string) -> int'], 'get the key identifier from a key name'),
        ('pygame.key.start_text_input', ['start_text_input() -> None'], 'start handling Unicode text input events'),
        ('pygame.key.stop_text_input', ['stop_text_input() -> None'], 'stop handling Unicode text input events'),
        ('pygame.key.set_text_input_rect', ['set_text_input_rect(Rect) -> None'], 'controls the position of the candidate list'),
    ]


MODULE_ID_PREFIX = "module-"


class CollectInfo(nodes.SparseNodeVisitor):
    def unknown_visit(self, node): pass
    def unknown_departure(self, node): pass

    def __init__(self, env, document_node):
        super().__init__(document_node)
        self.env = env
        self.summary_stack = [""]
        self.sig_stack = [[]]
        self.desc_stack = [[]]

    def depart_section(self, node):
        summary = self.summary_stack.pop()
        sigs = self.sig_stack.pop()
        child_descs = self.desc_stack.pop()
        refid = node["ids"][0]
        if node.children and node["ids"][0].startswith(MODULE_ID_PREFIX):
            self.env.pyg_descinfo_tbl[refid.removeprefix(MODULE_ID_PREFIX)] = {
                "fullname": node["names"][0],
                "summary": summary,
                "signatures": sigs,
                "children": [desc[0]["ids"][0] for desc in child_descs],
            }

    def visit_desc(self, _node):
        self.summary_stack.append("")
        self.sig_stack.append([])
        self.desc_stack.append([])

    def depart_desc(self, node):
        summary = self.summary_stack.pop()
        sigs = self.sig_stack.pop()
        child_descs = self.desc_stack.pop()
        refid = node[0]["ids"][0]
        self.env.pyg_descinfo_tbl[refid.removeprefix(MODULE_ID_PREFIX)] = {
            "fullname": node[0]["ids"][0],
            "summary": summary,
            "signatures": sigs,
            "children": [desc[0]["ids"][0] for desc in child_descs],
        }
        self.desc_stack[-1].append(node)

    def visit_inline(self, node):
        if "summaryline" in node["classes"]:
            self.summary_stack[-1] = node[0].astext()
        elif "signature" in node["classes"]:
            self.sig_stack[-1].append(node[0].astext())
        raise nodes.SkipDeparture()
