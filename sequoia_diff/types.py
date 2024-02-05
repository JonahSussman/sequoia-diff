# from __future__ import annotations # Potentially use this to clean up hints

from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict
import heapq

import tree_sitter as ts

@dataclass
class Rules:
  flattened: list[str]
  aliased:   dict[str, str]
  ignored:   list[str]

def fast_exp(base: int, exp: int):
  if exp == 0: return 1
  if exp == 1: return base

  result: int = 1
  while exp > 0:
    if (exp & 1) != 0: result *= base
    exp >>= 1
    base *= base

  return result


@dataclass
class Node:
  ts_node: ts.Node

  type: str
  start_byte: int
  end_byte: int
  label: Optional[str]

  children: list["Node"]
  parent: Optional["Node"]

  size: int # total number of nodes in this subtree including self
  height: int # edges to furthest leaf
  hash_value: int
  structure_hash_value: int

  def __hash__(self):
    return self.hash_value
  
  def __lt__(self, x):
    return self.type < x.type
  
  @staticmethod
  def from_tree_sitter_node(rules: Rules, ts_node: ts.Node) -> "Node":
    """
    Includes all children
    """
    # parse_and_translate
    
    if (ts_node.child_count == 0) or (ts_node.type in rules.flattened):
      label = ts_node.text.decode('utf-8')
    else:
      label = None

    output = Node(
      ts_node=ts_node,
      type=rules.aliased.get(ts_node.type, ts_node.type),
      start_byte=ts_node.start_byte,
      end_byte=ts_node.end_byte,
      label=label,
      children=[],
      parent=None,
      size=1,
      height=0,
      hash_value=0,
      structure_hash_value=0,
    )

    curr_hash=0
    curr_structure_hash=0

    if ts_node.type not in rules.flattened:
      for ts_child in ts_node.children:
        if ts_child.type in rules.ignored:
          continue

        output_child = Node.from_tree_sitter_node(rules, ts_child)
        output_child.parent = output
        output.children.append(output_child)

        output.height = max(output.height, output_child.height + 1)
        output.size += output_child.size
        curr_hash += output_child.hash_value
        curr_structure_hash += output_child.structure_hash_value

    output.hash_value = hash(hash(output.type) + hash(output.label) + curr_hash)
    output.structure_hash_value = hash(hash(output.type) + curr_structure_hash)

    return output

  @staticmethod
  def from_tree_sitter_tree(rules: dict, tree: ts.Tree) -> "Node":
    return Node.from_tree_sitter_node(rules, tree.root_node)
  
  def deep_copy(self) -> "Node":
    output = Node(
      ts_node=self.ts_node,
      type=self.type,
      start_byte=self.start_byte,
      end_byte=self.end_byte,
      label=self.label,
      children=[],
      parent=None,
      size=self.size,
      height=self.height,
      hash_value=self.hash_value,
      structure_hash_value=self.structure_hash_value,
    )

    for orig_child in self.children:
      child = orig_child.deep_copy()
      child.parent = output
      output.children.append(child)

    return output
  
  
  def preorder(self):
    yield self

    for child in self.children:
      gen = child.preorder()
      while (result := next(gen)) is not None:
        yield result

    while True: yield None

  def postorder(self):
    for child in self.children:
      gen = child.postorder()
      while (result := next(gen)) is not None:
        yield result

    yield self

    while True: yield None 

  def bfs(self):
    queue: list[Node] = [self]

    while len(queue) != 0:
      node = queue.pop(0)
      queue.extend(node.children)
      yield node

    while True: yield None

  def position_in_parent(self):
    if self.parent is None:
      return -1
    
    idx = 0
    for c in self.parent.children:
      if c is self: return idx
      idx += 1

    return -1

  def pretty_str(self, level=0) -> str:
    return f"{'  ' * level}{self.pretty_str_self()}\n" \
      + "".join([child.pretty_str(level + 1) for child in self.children])

  def pretty_str_self(self) -> str:
    return f"{self.type}{f': {self.label}' if self.label else ''} [{self.start_byte},{self.end_byte}]"

@dataclass
class MappingDict:
  src_to_dst: dict[Node, Node] = field(default_factory=lambda: defaultdict(lambda: None))
  dst_to_src: dict[Node, Node] = field(default_factory=lambda: defaultdict(lambda: None))

  def __len__(self):
    return len(self.src_to_dst)
  
  def __iter__(self):
    for src, dst in self.src_to_dst.items():
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

  def are_srcs_unmapped(self, srcs: list[Node]):
    for src in srcs:
      if src in self.src_to_dst:
        return False
      
    return True
  
  def are_dsts_unmapped(self, dsts: list[Node]):
    for dst in dsts:
      if dst in self.dst_to_src:
        return False
      
    return True
  
  def has_unmapped_src_children(self, node: Node):
    gen = node.preorder()
    next(gen)
    for child in gen:
      if child is None: break
      if child not in self.src_to_dst: return True

    return False
  
  def has_unmapped_dst_children(self, node: Node):
    gen = node.preorder()
    next(gen)
    for child in gen:
      if child is None: break
      if child not in self.dst_to_src: return True

    return False
  
  def is_mapping_allowed(self, src: Node, dst: Node):
    return src.type == dst.type \
      and src not in self.src_to_dst \
      and dst not in self.dst_to_src
  
@dataclass
class NodePriorityQueue:
  min_height: int = 1
  queue: list[tuple[int, Node]] = field(default_factory=list)

  def empty(self):
    return len(self.queue) == 0

  def push(self, node: Node):
    if node.height < self.min_height: 
      return
    heapq.heappush(self.queue, (-node.height, node))

  def push_children(self, node: Node):
    for child in node.children:
      self.push(child)

  def pop(self):
    return heapq.heappop(self.queue)

  def pop_equal_priority(self) -> tuple[Optional[int], list[Node]]:
    if self.empty(): return None, list[Node]()

    prio, node = heapq.heappop(self.queue)
    result = [node]
    while not self.empty() and self.queue[0][0] == prio:
      result.append(heapq.heappop(self.queue)[1])

    return prio, result
  
  def clear(self):
    self.queue.clear()

  def curr_prio(self):
    return self.queue[0][0]

def node_pq_synchronize(a: NodePriorityQueue, b: NodePriorityQueue) -> bool:
  while not (a.empty() or b.empty()) and (a.curr_prio() != b.curr_prio()):
    if a.curr_prio() > b.curr_prio():
      for node in a.pop_equal_priority()[1]: a.push_children(node)
    else:
      for node in b.pop_equal_priority()[1]: a.push_children(node)


  if a.empty() or b.empty():
    a.clear()
    b.clear()
    return False
    
  return True


@dataclass
class Insert:
  node: Node | ts.Node
  parent: Node | ts.Node
  pos: int
  name: str = "insert-node"

@dataclass
class Update:
  node: Node | ts.Node
  label: str
  value: str
  name: str = "update-node"

@dataclass
class Move:
  node: Node | ts.Node
  parent: Node | ts.Node
  pos: int
  name: str = "move-tree"

@dataclass
class Delete:
  node: Node | ts.Node
  name: str = 'delete-node'

Action = Insert | Update | Move | Delete