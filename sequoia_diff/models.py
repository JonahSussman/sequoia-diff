import hashlib
import heapq
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from pydantic import BaseModel, Field, RootModel


class LanguageRules(BaseModel):
    flattened: list[str] = []
    aliased: dict[str, str] = {}
    ignored: list[str] = []


class LanguageRuleSet(RootModel[dict[str, LanguageRules]]):
    root: dict[str, LanguageRules] = Field(..., title="LanguageRuleSet")


# TODO: Somehow add typing for orig_node. You could add a type parameter to
# Node, it's entirely possible that the parent or child of a Node could have a
# different type for orig_node. Thus, it would only work for one layer.
class Node:
    def __init__(
        self,
        type: str,
        label: Optional[str],
        orig_node: Optional[Any] = None,
        children: Optional[list["Node"]] = None,
        parent: Optional["Node"] = None,
    ):
        if children is None:
            children = []

        self.type = type  # Called "label" in the paper
        self.label = label  # Called "value" in the paper
        self.orig_node = orig_node

        # Fields modified through methods
        self.children: list["Node"] = []
        self.parent: Optional["Node"] = None

        for child in children:
            self.children_append(child)
        if parent is not None:
            self.set_parent(parent)

        # Lightweight statistics. Amortized O(1) time complexity
        self._needs_lightweight_recomputation: bool = True
        self._size: int = -1  # total number of nodes in this subtree including self
        self._height: int = -1  # edges to furthest leaf
        self._position_in_parent: int = -1
        self._hash_value: int = -1
        self._subtree_hash_value: int = -1

        # TODO: Implement heavy statistics

        # Heavy statistics. O(n) as it requires going through entire tree

        # self._dsu_parent: "Node" = parent if parent else self

        # self._idx_pre_ltr: int = -1
        # self._idx_post_ltr: int = -1
        # self._idx_pre_rtl: int = -1
        # self._idx_post_rtl: int = -1
        # self._lies_on_rightmost_path: bool = False
        # self._lies_on_leftmost_path: bool = False

    def __hash__(self):
        return self.hash_value

    def __lt__(self, other: "Node") -> bool:
        return (self.type, self.label) < (other.type, other.label)

    def __repr__(self):
        return f"Node(type={self.type}, label={self.label} at {hex(id(self))})"

    def deep_copy(self) -> "Node":
        result = Node(
            orig_node=self.orig_node,
            type=self.type,
            label=self.label,
            children=[],
            parent=None,
        )

        for orig_child in self.children:
            child = orig_child.deep_copy()
            result.children_append(child)

        return result

    def recompute_lightweight_stats(self):
        new_size = 1
        new_height = 0

        hasher = hashlib.new("sha256")

        hasher.update(
            f"{len(self.children) > 0}".encode("utf-8")
        )  # 0 if leaf, 1 if not
        hasher.update(self.type.encode("utf-8"))
        hasher.update(f"{self.label if self.label else ''}".encode("utf-8"))

        self._hash_value = int(hasher.hexdigest(), 16)

        for child in self.children:
            new_size += child.size
            new_height = max(new_height, child.height + 1)
            hasher.update(child.hash_value.to_bytes(32, "big"))

        self._size = new_size
        self._height = new_height
        self._subtree_hash_value = int(hasher.hexdigest(), 16)

        self._needs_lightweight_recomputation = False

    # def recompute_heavy_stats(self):
    #     for idx, node in enumerate(self.pre_order()):
    #         node._idx_pre_ltr = idx
    #         node._idx_pre_rtl = self.size - idx - 1
    #         if (parent := node.parent) is not None:
    #             node._lies_on_rightmost_path = parent.children[-1] is node
    #             node._lies_on_leftmost_path = parent.children[0] is node
    #         node._needs_heavy_recomputation = False

    #     for idx, node in enumerate(self.post_order()):
    #         node._idx_post_ltr = idx
    #         node._idx_post_rtl = self.size - idx - 1

    def needs_lightweight_recomputation(self):
        self._needs_lightweight_recomputation = True

        if self.parent is not None:
            self.parent.needs_lightweight_recomputation()

    # def needs_heavy_recomputation(self):
    #     self._needs_heavy_recomputation = True

    #     if self._dsu_parent is not self:
    #         self._dsu_parent.needs_heavy_recomputation()

    # Lightweight statistics properties

    @property
    def size(self):
        if self._needs_lightweight_recomputation:
            self.recompute_lightweight_stats()
        return self._size

    @property
    def height(self):
        if self._needs_lightweight_recomputation:
            self.recompute_lightweight_stats()
        return self._height

    @property
    def hash_value(self):
        if self._needs_lightweight_recomputation:
            self.recompute_lightweight_stats()
        return self._hash_value

    @property
    def subtree_hash_value(self):
        if self._needs_lightweight_recomputation:
            self.recompute_lightweight_stats()
        return self._subtree_hash_value

    @property
    def position_in_parent(self):
        # FIXME: This should be recomputed only when needed.
        self._position_in_parent = self.parent.children.index(self)

        return self._position_in_parent

    # Heavy statistics properties.

    # @property
    # def idx_pre_ltr(self):
    #     if self._needs_heavy_recomputation:
    #         self.recompute_heavy_stats()
    #     return self._idx_pre_ltr

    # @property
    # def idx_post_ltr(self):
    #     if self._needs_heavy_recomputation:
    #         self.recompute_heavy_stats()
    #     return self._idx_post_ltr

    # @property
    # def idx_pre_rtl(self):
    #     if self._needs_heavy_recomputation:
    #         self.recompute_heavy_stats()
    #     return self._idx_pre_rtl

    # @property
    # def idx_post_rtl(self):
    #     if self._needs_heavy_recomputation:
    #         self.recompute_heavy_stats()
    #     return self._idx_post_rtl

    # @property
    # def lies_on_rightmost_path(self):
    #     if self._needs_heavy_recomputation:
    #         self.recompute_heavy_stats()
    #     return self._lies_on_rightmost_path

    # @property
    # def lies_on_leftmost_path(self):
    #     if self._needs_heavy_recomputation:
    #         self.recompute_heavy_stats()
    #     return self._lies_on_leftmost_path

    # Tree modification methods

    def children_append(self, child: "Node"):
        self.children.append(child)
        child.parent = self
        # child._dsu_parent = self._dsu_parent

        child.needs_lightweight_recomputation()
        # child.needs_heavy_recomputation()

    def children_insert(self, index: int, child: "Node"):
        self.children.insert(index, child)
        child.parent = self
        # child._dsu_parent = self._dsu_parent

        child.needs_lightweight_recomputation()
        # child.needs_heavy_recomputation()

    def children_remove(self, child: "Node"):
        self.children.remove(child)
        child.parent = None
        # for node in child.pre_order():
        #     node._dsu_parent = node

        self.needs_lightweight_recomputation()
        # self.needs_heavy_recomputation()

        child.needs_lightweight_recomputation()
        # child.needs_heavy_recomputation()

    def set_parent(self, parent: Optional["Node"]):
        if self.parent is not None:
            self.parent.children_remove(self)

        if parent is not None:
            parent.children_append(self)

    # Traversal generators

    def pre_order(self, skip_self=False, rtl=False) -> Iterator["Node"]:
        if not skip_self:
            yield self

        if not rtl:
            for child in self.children:
                yield from child.pre_order()
        else:
            for child in reversed(self.children):
                yield from child.pre_order()

    def post_order(self, skip_self=False, rtl=False) -> Iterator["Node"]:
        if not rtl:
            for child in self.children:
                yield from child.post_order()
        else:
            for child in reversed(self.children):
                yield from child.post_order()

        if not skip_self:
            yield self

    def bfs(self) -> Iterator["Node"]:
        queue: list[Node] = [self]

        while len(queue) != 0:
            node = queue.pop(0)
            queue.extend(node.children)
            yield node

    # Printing methods

    def pretty_str(self, level=0) -> str:
        return f"{'  ' * level}{self.pretty_str_self()}\n" + "".join(
            [child.pretty_str(level + 1) for child in self.children]
        )

    def pretty_str_self(self) -> str:
        return f"{self.type}: {f'label={self.label}' if self.label else ''} subtree_hash={str(hex(self.subtree_hash_value))[:16]}"


@dataclass
class MappingDict:
    src_to_dst: dict[Node, Node] = field(default_factory=dict)
    dst_to_src: dict[Node, Node] = field(default_factory=dict)

    def __len__(self):
        return len(self.src_to_dst)

    def __iter__(self):
        for src, dst in self.items():
            yield (src, dst)

    def put(self, src: Node, dst: Node):
        self.src_to_dst[src] = dst
        self.dst_to_src[dst] = src

    def put_recursively(self, src: Node, dst: Node):
        self.put(src, dst)
        for i in range(len(src.children)):
            self.put(src.children[i], dst.children[i])

    def pop(self, src: Node, dst: Node):
        self.src_to_dst.pop(src)
        self.dst_to_src.pop(dst)

    def has(self, src: Node, dst: Node):
        if src not in self.src_to_dst:
            return False

        return self.src_to_dst[src] is dst

    def items(self, dst_to_src: bool = False):
        if dst_to_src:
            return self.dst_to_src.items()

        return self.src_to_dst.items()

    def are_srcs_unmapped(self, srcs: list[Node]):
        return all(src not in self.src_to_dst for src in srcs)

    def are_dsts_unmapped(self, dsts: list[Node]):
        return all(dst not in self.dst_to_src for dst in dsts)

    def has_unmapped_src_children(self, node: Node):
        return any(x not in self.src_to_dst for x in node.pre_order(True))

    def has_unmapped_dst_children(self, node: Node):
        return any(x not in self.dst_to_src for x in node.pre_order(True))

    def is_mapping_allowed(self, src: Node, dst: Node):
        return (
            src.type == dst.type
            and src not in self.src_to_dst
            and dst not in self.dst_to_src
        )


@dataclass
class NodePriorityQueue:
    """
    A priority queue for nodes. The priority is the height of the node, with
    larger heights being towards the front of the queue.
    """

    min_height: int = 1
    queue: list[tuple[int, Node]] = field(default_factory=list)

    def is_empty(self):
        """
        Returns if the queue is empty.
        """
        return len(self.queue) == 0

    def push(self, node: Node):
        """
        Push an element into the queue. If the height of the node is less than
        the minimum height, the node is not pushed.
        """
        if node.height < self.min_height:
            return
        heapq.heappush(self.queue, (-node.height, node))

    def push_children(self, node: Node):
        """
        Push all children of the node into the queue.
        """
        for child in node.children:
            self.push(child)

    def pop(self):
        """
        Pop the front element of the queue.
        """
        return heapq.heappop(self.queue)

    def pop_equal_priority(self) -> tuple[Optional[int], list[Node]]:
        """
        Pop all elements at the front of the queue that have the same priority.
        """
        if self.is_empty():
            return None, list[Node]()

        priority, node = heapq.heappop(self.queue)
        result = [node]
        while not self.is_empty() and self.queue[0][0] == priority:
            result.append(heapq.heappop(self.queue)[1])

        return priority, result

    def clear(self):
        """
        Remove all items from the queue.
        """
        self.queue.clear()

    def curr_priority(self):
        """
        Returns the priority of the front element of the queue.
        """
        return self.queue[0][0]

    def synchronize_and_push_children(self, other: "NodePriorityQueue") -> bool:
        """
        Special method that "unwinds" the queue, popping nodes and pushing their
        children until the priorities of the two queues match.
        """
        while not (self.is_empty() or other.is_empty()) and (
            self.curr_priority() != other.curr_priority()
        ):
            if self.curr_priority() > other.curr_priority():
                for node in self.pop_equal_priority()[1]:
                    self.push_children(node)
            else:
                for node in other.pop_equal_priority()[1]:
                    self.push_children(node)

        if self.is_empty() or other.is_empty():
            self.clear()
            other.clear()
            return False

        return True


@dataclass
class Insert:
    node: Node
    parent: Node
    pos: int

    @property
    def orig_node(self):
        return self.node.orig_node

    @orig_node.setter
    def orig_node(self, value):
        self.node.orig_node = value


@dataclass
class Update:
    node: Node
    label: str | None
    value: str

    @property
    def orig_node(self):
        return self.node.orig_node

    @orig_node.setter
    def orig_node(self, value):
        self.node.orig_node = value


@dataclass
class Move:
    node: Node
    parent: Node
    pos: int

    @property
    def orig_node(self):
        return self.node.orig_node

    @orig_node.setter
    def orig_node(self, value):
        self.node.orig_node = value


@dataclass
class Delete:
    node: Node

    @property
    def orig_node(self):
        return self.node.orig_node

    @orig_node.setter
    def orig_node(self, value):
        self.node.orig_node = value


Action = Insert | Update | Move | Delete
