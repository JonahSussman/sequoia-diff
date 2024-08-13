import unittest

from sequoia_diff.actions import generate_simplified_chawathe_edit_script, lcs
from sequoia_diff.models import MappingDict, Move, Node


class TestAlignChildren(unittest.TestCase):
    def test_align_children(self):
        t1 = Node(type="t1", label="t1")
        a1 = Node(type="a1", label="a1")
        b1 = Node(type="b1", label="b1")
        t1.children_append(a1)
        t1.children_append(b1)

        t2 = Node(type="t2", label="t2")
        b2 = Node(type="b2", label="b2")
        a2 = Node(type="a2", label="a2")
        t2.children_append(b2)
        t2.children_append(a2)

        mapping = MappingDict()
        mapping.put(t1, t2)
        mapping.put(a1, a2)
        mapping.put(b1, b2)

        actions = generate_simplified_chawathe_edit_script(mapping, t1, t2)

        self.assertEqual(len(actions), 1)
        self.assertTrue(isinstance(actions[0], Move))

        print(f"node: {actions[0].node}")
        print(f"parent: {actions[0].parent}")
        print(f"pos: {actions[0].pos}")


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


if __name__ == "__main__":
    unittest.main()
