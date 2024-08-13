import unittest

from sequoia_diff.actions import (
    align_children,
    find_pos,
    generate_simplified_chawathe_edit_script,
    lcs,
)
from sequoia_diff.models import Action, MappingDict, Move, Node
from tests.util import node


class TestAlignChildren(unittest.TestCase):
    def test_align_children_integration(self):
        t1 = Node(type="t1", label="t1")
        a1 = Node(type="a1", label="a1")
        b1 = Node(type="b1", label="b1")
        t1.children_append(a1)
        t1.children_append(b1)

        t2 = Node(type="t1", label="t1")
        b2 = Node(type="b1", label="b1")
        a2 = Node(type="a1", label="a1")
        t2.children_append(b2)
        t2.children_append(a2)

        mapping = MappingDict()
        mapping.put(t1, t2)
        mapping.put(a1, a2)
        mapping.put(b1, b2)

        expected_actions = [Move(node=a1, parent=t1, pos=1)]
        actions = generate_simplified_chawathe_edit_script(mapping, t1, t2)
        self.assertEqual(actions, expected_actions)

    def test_no_children(self):
        src = node("src")
        dst = node("dst")

        mappings = MappingDict()
        src_in_order: set[Node] = set()
        dst_in_order: set[Node] = set()

        expected_actions: list[Action] = []
        actions = align_children(src, dst, src_in_order, dst_in_order, mappings)
        self.assertEqual(actions, expected_actions)

    def test_no_misalignment(self):
        src = node("src", children=[node("a"), node("b"), node("c")])
        dst = node("dst", children=[node("a"), node("b"), node("c")])

        mappings = MappingDict()
        mappings.put(src.children[0], dst.children[0])
        mappings.put(src.children[1], dst.children[1])
        mappings.put(src.children[2], dst.children[2])

        src_in_order = set(src.children)
        dst_in_order = set(dst.children)

        expected_actions: list[Action] = []
        actions = align_children(src, dst, src_in_order, dst_in_order, mappings)
        self.assertEqual(actions, expected_actions)

    def test_simple_misalignment(self):
        src = node("src", children=[node("a"), node("b"), node("c")])
        dst = node("dst", children=[node("a"), node("c"), node("b")])

        mappings = MappingDict()
        mappings.put(src.children[0], dst.children[0])
        mappings.put(src.children[1], dst.children[2])
        mappings.put(src.children[2], dst.children[1])

        src_in_order = set(src.children)
        dst_in_order = set(dst.children)

        expected_actions = [Move(node=src.children[1], parent=src, pos=2)]
        actions = align_children(src, dst, src_in_order, dst_in_order, mappings)
        self.assertEqual(actions, expected_actions)

    def test_complex_misalignment(self):
        src = node("src", children=[node("a"), node("b"), node("c"), node("d")])
        dst = node("dst", children=[node("c"), node("a"), node("d"), node("b")])

        mappings = MappingDict()
        mappings.put(src.children[0], dst.children[1])
        mappings.put(src.children[1], dst.children[3])
        mappings.put(src.children[2], dst.children[0])
        mappings.put(src.children[3], dst.children[2])

        src_in_order: set[Node] = set()
        dst_in_order: set[Node] = set()

        expected_actions = [
            Move(node=src.children[0], parent=src, pos=2),
            Move(node=src.children[1], parent=src, pos=3),
        ]
        actions = align_children(src, dst, src_in_order, dst_in_order, mappings)
        self.assertEqual(actions, expected_actions)


class TestFindPos(unittest.TestCase):
    def test_node_with_no_parent(self):
        a = node("node")
        in_order: set[Node] = set()
        mappings = MappingDict()

        result = find_pos(a, in_order, mappings)
        self.assertEqual(result, 0)

    def test_leftmost_child_in_order(self):
        parent = node("parent", children=[node("a")])
        in_order = {parent.children[0]}
        mappings = MappingDict()

        result = find_pos(parent.children[0], in_order, mappings)
        self.assertEqual(result, 0)

    def test_no_siblings_in_order(self):
        parent = node("parent", children=[node("a"), node("b")])
        in_order: set[Node] = set()
        mappings = MappingDict()

        result = find_pos(parent.children[0], in_order, mappings)
        self.assertEqual(result, 0)

    def test_rightmost_sibling_in_order(self):
        # Test case where a rightmost sibling to the left of the node is in order
        parent = node(
            "parent", children=[node("sibling1"), node("sibling2"), node("node")]
        )
        in_order = {parent.children[1]}
        mappings = MappingDict()
        mappings.dst_to_src = {
            parent.children[1]: parent.children[1]
        }  # Mapping to itself for simplicity

        result = find_pos(parent.children[2], in_order, mappings)
        self.assertEqual(result, parent.children[1].position_in_parent + 1)

    def test_no_siblings_to_the_left(self):
        # Test case where the node has no siblings to the left (should return 0)
        parent = node("parent", children=[node("node")])
        in_order: set[Node] = set()
        mappings = MappingDict()

        result = find_pos(parent.children[0], in_order, mappings)
        self.assertEqual(result, 0)

    def test_node_with_in_order_siblings_and_mapping(self):
        # Test case with siblings marked in order and valid mappings
        parent = node(
            "parent", children=[node("sibling1"), node("sibling2"), node("node")]
        )
        in_order = {parent.children[0], parent.children[1]}
        mappings = MappingDict()
        mappings.dst_to_src = {
            parent.children[0]: parent.children[0],
            parent.children[1]: parent.children[1],
        }

        result = find_pos(parent.children[2], in_order, mappings)
        self.assertEqual(result, parent.children[1].position_in_parent + 1)

    def test_node_with_in_order_sibling_on_leftmost(self):
        # Test case where the leftmost sibling is marked in order
        parent = node(
            "parent", children=[node("sibling1"), node("sibling2"), node("node")]
        )
        in_order = {parent.children[0]}
        mappings = MappingDict()
        mappings.dst_to_src = {parent.children[0]: parent.children[0]}

        result = find_pos(parent.children[2], in_order, mappings)
        self.assertEqual(result, parent.children[0].position_in_parent + 1)


class TestLCS(unittest.TestCase):
    def test_basic_lcs(self):
        # Basic LCS case
        x = ["a", "b", "c", "d"]
        y = ["b", "c", "d", "e"]
        expected_result = [("b", "b"), ("c", "c"), ("d", "d")]
        self.assertEqual(lcs(x, y), expected_result)

    def test_lcs_with_no_common_elements(self):
        # No common elements
        x = ["a", "b", "c"]
        y = ["d", "e", "f"]
        expected_result: list[str] = []
        self.assertEqual(lcs(x, y), expected_result)

    def test_lcs_with_all_common_elements(self):
        # All elements in x and y are common
        x = ["a", "b", "c"]
        y = ["a", "b", "c"]
        expected_result = [("a", "a"), ("b", "b"), ("c", "c")]
        self.assertEqual(lcs(x, y), expected_result)

    def test_lcs_with_custom_equality_func(self):
        # Custom equality function (case-insensitive comparison)
        x = ["A", "b", "C"]
        y = ["a", "B", "c"]
        expected_result = [("A", "a"), ("b", "B"), ("C", "c")]
        self.assertEqual(
            lcs(x, y, equal=lambda a, b: a.lower() == b.lower()), expected_result
        )

    def test_lcs_with_empty_lists(self):
        # Edge case: one or both lists empty
        x: list[str] = []
        y: list[str] = ["a", "b", "c"]
        expected_result: list[str] = []
        self.assertEqual(lcs(x, y), expected_result)

        x = ["a", "b", "c"]
        y = []
        expected_result = []
        self.assertEqual(lcs(x, y), expected_result)

        x = []
        y = []
        expected_result = []
        self.assertEqual(lcs(x, y), expected_result)

    def test_lcs_with_repeating_elements(self):
        # Case with repeating elements
        x = ["a", "b", "a", "c", "b"]
        y = ["b", "a", "b", "c", "a"]
        expected_result = [("b", "b"), ("a", "a"), ("b", "b")]
        self.assertEqual(lcs(x, y), expected_result)

    def test_lcs_where_opt_jumps_to_y(self):
        # Test case where the optimal subsequence jumps to the next element in y
        x = ["a", "x", "c", "y", "z"]
        y = ["a", "b", "c", "z"]
        expected_result = [("a", "a"), ("c", "c"), ("z", "z")]
        self.assertEqual(lcs(x, y), expected_result)

    def test_lcs_with_optimal_jump_in_y(self):
        # Test case where there's an optimal jump in y
        x = ["a", "b", "c", "d", "e"]
        y = ["x", "b", "c", "f", "d"]
        expected_result = [("b", "b"), ("c", "c"), ("d", "d")]
        self.assertEqual(lcs(x, y), expected_result)
