import os
import unittest
from typing import cast
from unittest.mock import MagicMock, call, patch

import tree_sitter as ts
import yaml

# from sequoia_diff import SEQUOIA_RULES,
from sequoia_diff import get_tree_diff
from sequoia_diff.actions import generate_simplified_chawathe_edit_script
from sequoia_diff.loaders import PATH_TS_RULES, from_tree_sitter_tree
from sequoia_diff.matching import (
    generate_mappings,
    match_greedy_bottom_up,
    match_greedy_top_down,
)
from sequoia_diff.models import (
    Delete,
    Insert,
    LanguageRuleSet,
    MappingDict,
    Move,
    Node,
    Update,
)
from tests.util import PATH_DATA, TS_LANGUAGE_JAVA, node, read_and_parse_tree


class TestGetTreeAndAdjacent(unittest.TestCase):
    def setUp(self):
        self.PATH_MY_DATA = os.path.join(PATH_DATA, "test_sequoia_diff")

        FILE_PATH_BEFORE = os.path.join(self.PATH_MY_DATA, "0_0.java")
        FILE_PATH_AFTER = os.path.join(self.PATH_MY_DATA, "0_1.java")

        self.tree_before = read_and_parse_tree(TS_LANGUAGE_JAVA, FILE_PATH_BEFORE)
        self.tree_after = read_and_parse_tree(TS_LANGUAGE_JAVA, FILE_PATH_AFTER)

        with open(os.path.join(PATH_TS_RULES), "r") as f:
            self.rule_set = LanguageRuleSet.model_validate(yaml.safe_load(f))
        self.java_rules = self.rule_set.root.get("java")

    @patch("sequoia_diff.generate_simplified_chawathe_edit_script")
    @patch("sequoia_diff.generate_mappings")
    @patch("sequoia_diff.from_tree_sitter_tree")
    def test_get_tree_defaults(
        self,
        mock_from_tree_sitter_tree,
        mock_generate_mappings,
        mock_generate_simplified_chawathe_edit_script,
    ):
        old_tree = MagicMock()
        new_tree = MagicMock()
        loader = MagicMock()
        loader_args = [MagicMock()]

        # loader == None, loader_args == None
        manager = MagicMock()
        manager.attach_mock(mock_from_tree_sitter_tree, "from_tree_sitter_tree")
        manager.attach_mock(loader, "loader")

        get_tree_diff(old_tree, new_tree, None, None)
        manager.assert_has_calls(
            [
                call.from_tree_sitter_tree(old_tree, "java"),
                call.from_tree_sitter_tree(new_tree, "java"),
            ]
        )

        # loader != None, loader_args == None
        manager = MagicMock()
        manager.attach_mock(mock_from_tree_sitter_tree, "from_tree_sitter_tree")
        manager.attach_mock(loader, "loader")

        get_tree_diff(old_tree, new_tree, loader, None)
        manager.assert_has_calls(
            [
                call.loader(old_tree),
                call.loader(new_tree),
            ]
        )

        # loader == None, loader_args != None
        with self.assertRaises(ValueError):
            get_tree_diff(old_tree, new_tree, None, loader_args)

        # loader != None, loader_args != None
        manager = MagicMock()
        manager.attach_mock(mock_from_tree_sitter_tree, "from_tree_sitter_tree")
        manager.attach_mock(loader, "loader")

        get_tree_diff(old_tree, new_tree, loader, loader_args)
        manager.assert_has_calls(
            [
                call.loader(old_tree, *loader_args),
                call.loader(new_tree, *loader_args),
            ]
        )

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
        mappings = generate_mappings(
            from_tree_sitter_tree(self.tree_before, self.java_rules),
            from_tree_sitter_tree(self.tree_after, self.java_rules),
        )

        mapping_result = ""

        for a_node, b_node in mappings.items():
            a = cast(ts.Node, a_node.orig_node)
            b = cast(ts.Node, b_node.orig_node)

            self.assertEqual(a.type, b.type)

            mapping_result += f"{a.type} [{a.start_byte}, {a.end_byte}] <-> {b.type} [{b.start_byte}, {b.end_byte}]\n"

        with open(os.path.join(self.PATH_MY_DATA, "0_mappings.txt"), "r") as f:
            expected_mapping_result = f.read()

        self.assertEqual(mapping_result, expected_mapping_result)

    def test_get_tree_diff(self):
        actions = get_tree_diff(
            self.tree_before, self.tree_after, from_tree_sitter_tree, [self.java_rules]
        )

        def s(a: Node):
            if a is None:
                return "None"

            o = cast(ts.Node, a.orig_node)
            return f"{o.type} [{o.start_byte}, {o.end_byte}]"

        actions_result = ""

        # TODO: Make this a util function that translates actions to some kind
        # of yaml format.
        for a in actions:
            if isinstance(a, Insert):
                actions_result += f"""- insert_node:\n    node: {s(a.node)}\n    parent: {s(a.parent)}\n    pos: {a.pos}\n"""
            elif isinstance(a, Update):
                actions_result += f"""- update_node:\n    node: {s(a.node)}\n    label: {a.label}\n    value: {a.value}\n"""
            elif isinstance(a, Move):
                actions_result += f"""- move_node:\n    node: {s(a.node)}\n    parent: {s(a.parent)}\n    pos: {a.pos}\n"""
            elif isinstance(a, Delete):
                actions_result += f"""- delete_node:\n    node: {s(a.node)}\n"""

        with open(os.path.join(self.PATH_MY_DATA, "0_actions.yaml"), "r") as f:
            expected_actions_result = f.read()

        self.assertEqual(actions_result, expected_actions_result)

    def test_mappings_inside(self):
        src = node("root", children=[node("a"), node("b")])
        dst = node("root", children=[node("a"), node("c"), node("b")])

        mappings = MappingDict()
        # mappings.put(src.children[0], dst.children[0])
        # mappings.put(src.children[1], dst.children[2])

        src_in_order, dst_in_order = set(), set()

        mappings = MappingDict()
        match_greedy_top_down(mappings, src, dst)
        self.assertEqual(list(mappings.items()), [])

        match_greedy_bottom_up(mappings, src, dst)
        expected_mappings = [
            (src, dst),
            (src.children[0], dst.children[0]),
            (src.children[1], dst.children[2]),
        ]

        self.assertEqual(list(mappings.items()), expected_mappings)

        expected_actions = [Insert(node=dst.children[1], parent=src, pos=1)]
        actions = generate_simplified_chawathe_edit_script(mappings, src, dst)
        self.assertEqual(actions, expected_actions)
