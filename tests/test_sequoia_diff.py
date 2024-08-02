import os
import unittest

from tree_sitter import Language, Parser

from sequoia_diff import SEQUOIA_RULES, get_tree_diff
from sequoia_diff.matching import generate_mappings
from sequoia_diff.types import Delete, Insert, MappingDict, Move, Node, Update

# Constants

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

TS_OUTPUT_PATH = os.path.join(
    CURRENT_PATH, "../tree-sitter-java-build/language-java.so"
)
TS_REPO_PATHS = [os.path.join(CURRENT_PATH, "../tree-sitter-java/")]
TS_NAME = "java"

Language.build_library(TS_OUTPUT_PATH, TS_REPO_PATHS)
TS_JAVA_LANGUAGE = Language(TS_OUTPUT_PATH, TS_NAME)

FILE_PATH_BEFORE = os.path.join(CURRENT_PATH, "data/ExampleClass.java")
FILE_PATH_AFTER = os.path.join(CURRENT_PATH, "data/ExampleClassAfterChange.java")


class TestSequoiaDiff(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()
        self.parser.set_language(TS_JAVA_LANGUAGE)

        with open(FILE_PATH_BEFORE, "r") as f:
            file_before = f.read()
        self.tree_before = self.parser.parse(bytes(file_before, "utf-8"))

        with open(FILE_PATH_AFTER, "r") as f:
            file_after = f.read()
        self.tree_after = self.parser.parse(bytes(file_after, "utf-8"))

    def test_node_from_tree_sitter_tree(self):
        self.assertEqual(self.tree_before.root_node.descendant_count, 48)

        Node.from_tree_sitter_tree(SEQUOIA_RULES["java"], self.tree_before)
        # print(node.pretty_str())
        # TODO: Add more assertions

    def test_mapping_dict(self):
        node = Node.from_tree_sitter_tree(SEQUOIA_RULES["java"], self.tree_before)

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
            Node.from_tree_sitter_tree(SEQUOIA_RULES["java"], self.tree_before),
            Node.from_tree_sitter_tree(SEQUOIA_RULES["java"], self.tree_after),
        )

        for a, b in x.dst_to_src.items():
            print(
                f"{a.type} [{a.start_byte}, {a.end_byte}] <-> {b.type} [{b.start_byte}, {b.end_byte}]"
            )

    def test_get_tree_diff(self):
        actions = get_tree_diff("java", self.tree_before, self.tree_after)

        import tree_sitter as ts

        def s(a: ts.Node):
            if a is None:
                return "None"
            return f"{a.type} [{a.start_byte}, {a.end_byte}]"

        for a in actions:
            if isinstance(a, Insert):
                print(
                    f"""{a.name}\n- node: {s(a.node)}\n- parent: {s(a.parent)}\n- pos: {a.pos}"""
                )
            elif isinstance(a, Update):
                print(
                    f"""{a.name}\n- node: {s(a.node)}\n- label: {a.label}\n- value: {a.value}"""
                )
            elif isinstance(a, Move):
                print(
                    f"""{a.name}\n- node: {s(a.node)}\n- parent: {s(a.parent)}\n- pos: {a.pos}"""
                )
            elif isinstance(a, Delete):
                print(f"""{a.name}\n- node: {s(a.node)}""")
