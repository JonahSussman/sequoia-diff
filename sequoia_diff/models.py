import hashlib
import heapq
from dataclasses import dataclass, field
from typing import Any, ItemsView, Iterator, Optional

from pydantic.fields import Field
from pydantic.main import BaseModel
from pydantic.root_model import RootModel


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
        self._subtree_type_hash_value: int = -1

        # TODO: Implement heavy statistics

        # Heavy statistics. O(n) as it requires going through entire tree

        # self._dsu_parent: "Node" = parent if parent else self

        # self._idx_pre_ltr: int = -1
        # self._idx_post_ltr: int = -1
        # self._idx_pre_rtl: int = -1
        # self._idx_post_rtl: int = -1
        # self._lies_on_rightmost_path: bool = False
        # self._lies_on_leftmost_path: bool = False

    def __hash__(self) -> int:
        return self.hash_value

    def __lt__(self, other: "Node") -> bool:
        return (self.type, self.label) < (other.type, other.label)

    def __repr__(self) -> str:
        return (
            f"Node("
            f"type={self.type!r}, "
            f"label={self.label!r}, "
            f"len(children)={len(self.children)}, "
            f"parent={self.parent!r}) "
            f"at {id(self)})"
        )

    def deep_copy(self) -> "Node":
        """
        Creates a deep copy of the node and its subtree.
        """
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

    def recompute_lightweight_stats(self) -> None:
        """
        Recomputes some statistics about the node and its subtree. Note, because
        the statistics are tagged with `@property`, each child's statistics will
        be recursively computed as well.
        """
        new_size = 1
        new_height = 0

        type_label_hasher = hashlib.new("sha256")
        type_hasher = hashlib.new("sha256")

        # 0 if leaf, 1 if not
        type_label_hasher.update(f"{len(self.children) > 0}".encode("utf-8"))
        type_label_hasher.update(self.type.encode("utf-8"))
        type_label_hasher.update(f"{self.label if self.label else ''}".encode("utf-8"))

        type_hasher.update(f"{len(self.children) > 0}".encode("utf-8"))
        type_hasher.update(self.type.encode("utf-8"))

        self._hash_value = int(type_label_hasher.hexdigest(), 16)

        for child in self.children:
            new_size += child.size
            new_height = max(new_height, child.height + 1)

            type_label_hasher.update(child.subtree_hash_value.to_bytes(32, "big"))
            type_hasher.update(child.subtree_type_hash_value.to_bytes(32, "big"))

        self._size = new_size
        self._height = new_height
        self._subtree_hash_value = int(type_label_hasher.hexdigest(), 16)
        self._subtree_type_hash_value = int(type_hasher.hexdigest(), 16)

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

    def needs_lightweight_recomputation(self) -> None:
        """
        After certain edit operations, we need to let the node know that it
        needs to lazily recompute some statistics.
        """
        self._needs_lightweight_recomputation = True

        if self.parent is not None:
            self.parent.needs_lightweight_recomputation()

    # def needs_heavy_recomputation(self):
    #     self._needs_heavy_recomputation = True

    #     if self._dsu_parent is not self:
    #         self._dsu_parent.needs_heavy_recomputation()

    # Lightweight statistics properties

    @property
    def size(self) -> int:
        """
        The total number of nodes in this subtree including self
        """
        if self._needs_lightweight_recomputation:
            self.recompute_lightweight_stats()
        return self._size

    @property
    def height(self) -> int:
        """
        The number of edges to self's furthest leaf
        """
        if self._needs_lightweight_recomputation:
            self.recompute_lightweight_stats()
        return self._height

    @property
    def hash_value(self) -> int:
        """
        Hash value of ne node, considering the data relevant to this node only
        (type, label). Does not consider the children.
        """
        if self._needs_lightweight_recomputation:
            self.recompute_lightweight_stats()
        return self._hash_value

    @property
    def subtree_hash_value(self) -> int:
        """
        Hash value of the subtree rooted at this node, considering the types and
        labels of the nodes.
        """
        if self._needs_lightweight_recomputation:
            self.recompute_lightweight_stats()
        return self._subtree_hash_value

    @property
    def subtree_type_hash_value(self) -> int:
        """
        Hash value of the subtree rooted at this node, only considering the
        types of the nodes.
        """
        if self._needs_lightweight_recomputation:
            self.recompute_lightweight_stats()
        return self._subtree_type_hash_value

    @property
    def position_in_parent(self) -> int:
        """
        The index of this node in its parent's children list.
        """
        # FIXME: This should be recomputed only when needed.
        if self.parent is None:
            self._position_in_parent = -1
        else:
            # If using .index, the whole library hangs for some reason
            for idx, child in enumerate(self.parent.children):
                if child is self:
                    self._position_in_parent = idx
                    break

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

    def children_append(self, child: "Node") -> None:
        """
        Appends a child to the node and sets the parent of the child to the
        node.
        """
        self.children.append(child)
        child.parent = self
        # child._dsu_parent = self._dsu_parent

        child.needs_lightweight_recomputation()
        # child.needs_heavy_recomputation()

    def children_insert(self, index: int, child: "Node") -> None:
        """
        Inserts a child to the node at the specified index and sets the parent
        of the child to the node.
        """
        self.children.insert(index, child)
        child.parent = self
        # child._dsu_parent = self._dsu_parent

        child.needs_lightweight_recomputation()
        # child.needs_heavy_recomputation()

    def children_remove(self, child: "Node") -> None:
        """
        Removes the specified child from the node's children and sets the parent
        of the child to None.
        """
        self.children.remove(child)
        child.parent = None
        # for node in child.pre_order():
        #     node._dsu_parent = node

        self.needs_lightweight_recomputation()
        # self.needs_heavy_recomputation()

        child.needs_lightweight_recomputation()
        # child.needs_heavy_recomputation()

    def set_parent(self, parent: Optional["Node"]) -> None:
        """
        Sets the parent of the node to the specified parent. If the node already
        has a parent, it removes itself from the previous parent's children
        list.
        """
        if self.parent is not None:
            self.parent.children_remove(self)

        if parent is not None:
            parent.children_append(self)

    # Traversal generators

    def pre_order(self, skip_self: bool = False, rtl: bool = False) -> Iterator["Node"]:
        if not skip_self:
            yield self

        if not rtl:
            for child in self.children:
                yield from child.pre_order()
        else:
            for child in reversed(self.children):
                yield from child.pre_order()

    def post_order(
        self, skip_self: bool = False, rtl: bool = False
    ) -> Iterator["Node"]:
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

    def pretty_str(self, level: int = 0, full_hash: bool = False) -> str:
        return f"{'  ' * level}{self.pretty_str_self(full_hash)}\n" + "".join(
            [child.pretty_str(level + 1, full_hash) for child in self.children]
        )

    def pretty_str_self(self, full_hash: bool = False) -> str:
        # NOTE: There might be a better way to do this...
        a: list[str] = [f'type="{self.type}"']

        if self.label:
            a.append(f'label="{self.label}"')

        if full_hash:
            a.append(f"subtree_hash={hex(self.subtree_hash_value)}")
        else:
            a.append(f"subtree_hash={hex(self.subtree_hash_value)[:13]}...")

        return f"{self.__class__.__name__}({', '.join(a)})"


@dataclass
class MappingDict:
    src_to_dst: dict[Node, Node] = field(default_factory=dict)
    dst_to_src: dict[Node, Node] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.src_to_dst)

    def __iter__(self) -> Iterator[ItemsView[Node, Node]]:
        for item in self.items():
            yield item

    def put(self, src: Node, dst: Node) -> None:
        self.src_to_dst[src] = dst
        self.dst_to_src[dst] = src

    def put_recursively(self, src: Node, dst: Node) -> None:
        self.put(src, dst)
        for i in range(len(src.children)):
            self.put_recursively(src.children[i], dst.children[i])

    def pop(self, src: Node, dst: Node) -> tuple[Node, Node]:
        return (self.src_to_dst.pop(src), self.dst_to_src.pop(dst))

    def has(self, src: Node, dst: Node) -> bool:
        if src not in self.src_to_dst:
            return False

        return self.src_to_dst[src] is dst

    def items(self, dst_to_src: bool = False) -> ItemsView[Node, Node]:
        if dst_to_src:
            return self.dst_to_src.items()

        return self.src_to_dst.items()

    def are_srcs_unmapped(self, srcs: list[Node]) -> bool:
        return all(src not in self.src_to_dst for src in srcs)

    def are_dsts_unmapped(self, dsts: list[Node]) -> bool:
        return all(dst not in self.dst_to_src for dst in dsts)

    def has_unmapped_src_children(self, node: Node) -> bool:
        return any(x not in self.src_to_dst for x in node.pre_order(True))

    def has_unmapped_dst_children(self, node: Node) -> bool:
        return any(x not in self.dst_to_src for x in node.pre_order(True))

    def is_mapping_allowed(self, src: Node, dst: Node) -> bool:
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

    def is_empty(self) -> bool:
        """
        Returns if the queue is empty.
        """
        return len(self.queue) == 0

    def push(self, node: Node) -> None:
        """
        Push an element into the queue. If the height of the node is less than
        the minimum height, the node is not pushed.
        """
        if node.height < self.min_height:
            return
        heapq.heappush(self.queue, (-node.height, node))

    def push_children(self, node: Node) -> None:
        """
        Push all children of the node into the queue.
        """
        for child in node.children:
            self.push(child)

    def pop(self) -> tuple[int, Node]:
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

    def clear(self) -> None:
        """
        Remove all items from the queue.
        """
        self.queue.clear()

    def curr_priority(self) -> int:
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
    whole_subtree: bool = False

    @property
    def orig_node(self) -> Optional[Any]:
        return self.node.orig_node

    @orig_node.setter
    def orig_node(self, value: Optional[Any]) -> None:
        self.node.orig_node = value


@dataclass
class Update:
    node: Node
    old_label: Optional[str]
    new_label: Optional[str]

    @property
    def orig_node(self) -> Optional[Any]:
        return self.node.orig_node

    @orig_node.setter
    def orig_node(self, value: Optional[Any]) -> None:
        self.node.orig_node = value


@dataclass
class Move:
    node: Node
    parent: Node
    pos: int

    @property
    def orig_node(self) -> Optional[Any]:
        return self.node.orig_node

    @orig_node.setter
    def orig_node(self, value: Optional[Any]) -> None:
        self.node.orig_node = value


@dataclass
class Delete:
    node: Node

    @property
    def orig_node(self) -> Optional[Any]:
        return self.node.orig_node

    @orig_node.setter
    def orig_node(self, value: Optional[Any]) -> None:
        self.node.orig_node = value


Action = Insert | Update | Move | Delete
