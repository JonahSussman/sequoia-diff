import logging
import os
import unittest
from unittest.mock import MagicMock, call, patch

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
from sequoia_diff.models import Insert, LanguageRuleSet, MappingDict, Node
from tests.util import (
    PATH_DATA,
    TS_LANGUAGE_JAVA,
    dictize_action,
    dictize_mappings,
    node,
    read_and_parse_tree,
)


class TestGetTreeAndAdjacent(unittest.TestCase):
    def setUp(self):
        self.PATH_MY_DATA = os.path.join(PATH_DATA, "test_sequoia_diff")

        FILE_PATH_BEFORE = os.path.join(self.PATH_MY_DATA, "0/before.java")
        FILE_PATH_AFTER = os.path.join(self.PATH_MY_DATA, "0/after.java")

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

    def test_mappings_inside(self):
        src = node("root", children=[node("a"), node("b")])
        dst = node("root", children=[node("a"), node("c"), node("b")])

        mappings = MappingDict()
        # mappings.put(src.children[0], dst.children[0])
        # mappings.put(src.children[1], dst.children[2])

        mappings = MappingDict()
        match_greedy_top_down(mappings, src, dst)
        expected_mappings: list[tuple[Node, Node]] = [
            # (src.children[0], dst.children[0]),
            # (src.children[1], dst.children[2]),
        ]
        self.assertEqual(list(mappings.items()), expected_mappings)

        match_greedy_bottom_up(mappings, src, dst)
        expected_mappings = [
            (src, dst),
            (src.children[0], dst.children[0]),
            (src.children[1], dst.children[2]),
        ]
        self.assertEqual(list(mappings.items()), expected_mappings)

        expected_actions = [
            Insert(node=dst.children[1], parent=src, pos=1, whole_subtree=True)
        ]
        actions = generate_simplified_chawathe_edit_script(mappings, src, dst)
        self.assertEqual(actions, expected_actions)

    def test_test_cases(self):
        # get all folders in PATH_MY_DATA
        test_cases_dirs: list[str] = []
        for d in os.listdir(self.PATH_MY_DATA):
            test_case_dir = os.path.join(self.PATH_MY_DATA, d)
            if os.path.isdir(test_case_dir):
                test_cases_dirs.append(test_case_dir)

        DEBUG_CASE = None

        for test_case_dir in test_cases_dirs:
            test_case_id = test_case_dir[len(self.PATH_MY_DATA) + 1 :]
            test_case_name = f"test_test_cases {test_case_id}"

            if DEBUG_CASE is not None and test_case_id != DEBUG_CASE:
                continue

            logging.debug(f"Running test case: {test_case_name}")

            # load actions.yaml, mappings.txt, before.java, after.java
            with open(os.path.join(test_case_dir, "actions.yaml"), "r") as f:
                expected_actions_result = yaml.safe_load(f.read())
            with open(os.path.join(test_case_dir, "mappings.yaml"), "r") as f:
                expected_mapping_result = yaml.safe_load(f.read())

            with open(os.path.join(test_case_dir, "before.java"), "r") as f:
                tree_before = read_and_parse_tree(TS_LANGUAGE_JAVA, f)
                node_before = from_tree_sitter_tree(tree_before, self.java_rules)
            with open(os.path.join(test_case_dir, "after.java"), "r") as f:
                tree_after = read_and_parse_tree(TS_LANGUAGE_JAVA, f)
                node_after = from_tree_sitter_tree(tree_after, self.java_rules)

            actions = [
                dictize_action(action)
                for action in get_tree_diff(node_before, node_after)
            ]

            mappings = [
                m for m in dictize_mappings(generate_mappings(node_before, node_after))
            ]

            self.assertEqual(
                actions,
                expected_actions_result,
                "Failed on test case: " + test_case_name,
            )

            self.assertEqual(
                mappings,
                expected_mapping_result,
                "Failed on test case: " + test_case_name,
            )
