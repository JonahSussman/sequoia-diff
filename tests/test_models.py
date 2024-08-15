import logging
import unittest
from hashlib import sha256
from unittest.mock import MagicMock

from sequoia_diff.models import Delete, Insert, Move, Node, Update
from tests.util import node


class TestNode(unittest.TestCase):

    def setUp(self):
        self.root = Node(type="root", label="root_node")
        self.child1 = Node(type="child1", label="child_node_1")
        self.child2 = Node(type="child2", label="child_node_2")

    def test_initialization(self):
        node = Node(type="root", label="root_node")
        logging.debug(node)

        self.assertEqual(node.type, "root")
        self.assertEqual(node.label, "root_node")
        self.assertIsNone(node.orig_node)
        self.assertEqual(node.children, [])
        self.assertIsNone(node.parent)
        self.assertTrue(node._needs_lightweight_recomputation)

    def test_deep_copy(self):
        self.root.children_append(self.child1)
        self.root.children_append(self.child2)
        copy = self.root.deep_copy()

        self.assertEqual(copy.type, self.root.type)
        self.assertEqual(copy.label, self.root.label)
        self.assertEqual(len(copy.children), len(self.root.children))
        self.assertNotEqual(copy, self.root)  # Ensure it's a new object
        self.assertIsNone(copy.parent)
        self.assertEqual(copy.children[0].type, self.child1.type)
        self.assertEqual(copy.children[1].type, self.child2.type)

    def test_recompute_lightweight_stats(self):
        self.root.children_append(self.child1)
        self.root.children_append(self.child2)
        self.root.recompute_lightweight_stats()

        hasher = sha256()
        hasher.update(f"{len(self.root.children) > 0}".encode("utf-8"))
        hasher.update(self.root.type.encode("utf-8"))
        hasher.update(self.root.label.encode("utf-8"))

        child1_hash = self.child1.hash_value.to_bytes(32, "big")
        child2_hash = self.child2.hash_value.to_bytes(32, "big")
        hasher.update(child1_hash)
        hasher.update(child2_hash)
        expected_subtree_hash_value = int(hasher.hexdigest(), 16)

        self.assertEqual(self.root.size, 3)
        self.assertEqual(self.root.height, 1)
        self.assertEqual(self.root.subtree_hash_value, expected_subtree_hash_value)

    def test_needs_lightweight_recomputation(self):
        self.root.children_append(self.child1)
        self.root.recompute_lightweight_stats()
        self.root.needs_lightweight_recomputation()

        self.assertTrue(self.root._needs_lightweight_recomputation)
        self.assertFalse(self.child1._needs_lightweight_recomputation)

    def test_tree_modification_methods(self):
        # Append child
        self.root.children_append(self.child1)
        self.assertEqual(len(self.root.children), 1)
        self.assertEqual(self.root.children[0], self.child1)
        self.assertEqual(self.child1.parent, self.root)
        self.assertEqual(self.root.size, 2)

        # Insert child
        new_child = Node(type="new_child", label="new_child_node")
        self.root.children_insert(0, new_child)
        self.assertEqual(self.root.children[0], new_child)
        self.assertEqual(new_child.parent, self.root)
        self.assertEqual(self.root.size, 3)

        # Remove child
        self.root.children_remove(self.child1)
        self.assertEqual(len(self.root.children), 1)
        self.assertIsNone(self.child1.parent)
        self.assertEqual(self.root.size, 2)

        # Set parent
        self.child1.set_parent(self.root)
        self.assertEqual(self.child1.parent, self.root)
        self.assertIn(self.child1, self.root.children)
        self.assertEqual(self.root.size, 3)

    def test_traversal_methods(self):
        self.root.children_append(self.child1)
        self.root.children_append(self.child2)
        child1_1 = Node(type="child1_1", label="child_node_1_1")
        self.child1.children_append(child1_1)

        # Test pre_order
        pre_order_result = list(self.root.pre_order())
        self.assertEqual(
            pre_order_result, [self.root, self.child1, child1_1, self.child2]
        )

        # Test post_order
        post_order_result = list(self.root.post_order())
        self.assertEqual(
            post_order_result, [child1_1, self.child1, self.child2, self.root]
        )

        # Test bfs
        bfs_result = list(self.root.bfs())
        self.assertEqual(bfs_result, [self.root, self.child1, self.child2, child1_1])

    def test_hash_value(self):
        self.assertEqual(node("a").subtree_hash_value, node("a").subtree_hash_value)


class TestAction(unittest.TestCase):
    def test_orig_node(self):
        mock_a = MagicMock()
        mock_b = MagicMock()

        def new_node():
            return Node(type="mock", label="mock", orig_node=mock_a)

        dummy = MagicMock()

        i = Insert(new_node(), dummy, dummy)
        self.assertIs(i.orig_node, mock_a)
        i.orig_node = mock_b
        self.assertIs(i.orig_node, mock_b)

        u = Update(new_node(), dummy, dummy)
        self.assertIs(u.orig_node, mock_a)
        u.orig_node = mock_b
        self.assertIs(u.orig_node, mock_b)

        d = Delete(new_node())
        self.assertIs(d.orig_node, mock_a)
        d.orig_node = mock_b
        self.assertIs(d.orig_node, mock_b)

        m = Move(new_node(), dummy, dummy)
        self.assertIs(m.orig_node, mock_a)
        m.orig_node = mock_b
        self.assertIs(m.orig_node, mock_b)
