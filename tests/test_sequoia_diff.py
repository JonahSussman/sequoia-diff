import os
import unittest
from typing import cast

import tree_sitter as ts
import yaml

# from sequoia_diff import SEQUOIA_RULES,
from sequoia_diff import get_tree_diff
from sequoia_diff.loaders import PATH_TS_RULES, from_tree_sitter_tree
from sequoia_diff.matching import generate_mappings
from sequoia_diff.models import (
    Delete,
    Insert,
    LanguageRuleSet,
    MappingDict,
    Move,
    Node,
    Update,
)
from tests.util import PATH_TESTS, TS_LANGUAGE_JAVA, read_and_parse_tree


class TestSequoiaDiff(unittest.TestCase):
    def setUp(self):
        FILE_PATH_BEFORE = os.path.join(PATH_TESTS, "data/ExampleClass.java")
        FILE_PATH_AFTER = os.path.join(PATH_TESTS, "data/ExampleClassAfterChange.java")

        self.tree_before = read_and_parse_tree(TS_LANGUAGE_JAVA, FILE_PATH_BEFORE)
        self.tree_after = read_and_parse_tree(TS_LANGUAGE_JAVA, FILE_PATH_AFTER)

        with open(os.path.join(PATH_TS_RULES), "r") as f:
            self.rule_set = LanguageRuleSet.model_validate(yaml.safe_load(f))
        self.java_rules = self.rule_set.root.get("java")

    def test_node_from_tree_sitter_tree(self):
        self.assertEqual(self.tree_before.root_node.descendant_count, 48)

        from_tree_sitter_tree(self.tree_before, self.java_rules)

    def test_mapping_dict(self):
        node = from_tree_sitter_tree(self.tree_before, self.java_rules)

        node_b = node.children[0]
        m = MappingDict()
        m.put(node, node_b)

        m_set = set(m)
        self.assertEqual(len(m_set), 1)

        x = (id(node), id(node_b))
        nodes = m_set.pop()
        y = (id(nodes[0]), id(nodes[1]))

        self.assertEqual(x, y)

    def test_mappings(self):
        x = generate_mappings(
            from_tree_sitter_tree(self.tree_before, self.java_rules),
            from_tree_sitter_tree(self.tree_after, self.java_rules),
        )

        for a_node, b_node in x.dst_to_src.items():
            a = cast(ts.Node, a_node.orig_node)
            b = cast(ts.Node, b_node.orig_node)

            print(
                f"{a.type} [{a.start_byte}, {a.end_byte}] <-> {b.type} [{b.start_byte}, {b.end_byte}]"
            )

    def test_get_tree_diff(self):
        actions = get_tree_diff(
            self.tree_before, self.tree_after, from_tree_sitter_tree, [self.java_rules]
        )

        def s(a: Node):
            if a is None:
                return "None"

            o = cast(ts.Node, a.orig_node)
            return f"{o.type} [{o.start_byte}, {o.end_byte}]"

        for a in actions:
            if isinstance(a, Insert):
                print(
                    f"""insert_node\n- node: {s(a.node)}\n- parent: {s(a.parent)}\n- pos: {a.pos}"""
                )
            elif isinstance(a, Update):
                print(
                    f"""update_node\n- node: {s(a.node)}\n- label: {a.label}\n- value: {a.value}"""
                )
            elif isinstance(a, Move):
                print(
                    f"""move_node\n- node: {s(a.node)}\n- parent: {s(a.parent)}\n- pos: {a.pos}"""
                )
            elif isinstance(a, Delete):
                print(f"""delete_node\n- node: {s(a.node)}""")
