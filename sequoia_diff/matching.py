from collections import defaultdict
from typing import Callable, Optional
from queue import PriorityQueue
import sys

from sequoia_diff.types import MappingDict, Node, NodePriorityQueue, node_pq_synchronize
from sequoia_diff.string_comparisons import normalized_tri_gram_distance

MatchingFunc = Callable[[MappingDict, Node, Node], MappingDict]

def number_of_mapped_descendants(mappings: MappingDict, src: Node, dst: Node):
  dst_descendants: set[Node] = set()
  for node in dst.preorder():
    if node is dst: continue
    if node is None: break
    dst_descendants.add(node)

  mapped_descendants: int = 0

  for node in src.preorder():
    if node is src: continue
    if node is None: break
    if node not in mappings.src_to_dst: continue

    dst_for_src_descendant = mappings.src_to_dst[node]
    if dst_for_src_descendant in dst_descendants:
      mapped_descendants += 1

  return mapped_descendants

def dice_coefficient(common: int, left: int, right: int):
  return 2.0 * common / (left + right)

def dice_similarity(mappings: MappingDict, src: Node, dst: Node):
  return dice_coefficient(
    number_of_mapped_descendants(mappings, src, dst),
    src.size, dst.size
  )


def match_greedy_subtree(mappings: MappingDict, src: Node, dst: Node):
  ambiguous_mappings: list[tuple[set[Node], set[Node]]] = []

  pq_src = NodePriorityQueue()
  pq_dst = NodePriorityQueue()

  pq_src.push(src)
  pq_dst.push(dst)

  while node_pq_synchronize(pq_src, pq_dst):
    _, src_nodes = pq_src.pop_equal_priority()
    _, dst_nodes = pq_dst.pop_equal_priority()

    local_mappings: dict[int, tuple[set[Node], set[Node]]] = defaultdict(
      lambda: (set(), set())
    )

    for node in src_nodes:
      local_mappings[hash(node)][0].add(node)
    for node in dst_nodes:
      local_mappings[hash(node)][1].add(node)

    for key, value in local_mappings.items():
      if len(value[0]) == 0 or len(value[1]) == 0: # unmapped
        for node in value[0]: pq_src.push_children(node)
        for node in value[1]: pq_dst.push_children(node)
        pass
      elif len(value[0]) == 1 and len(value[1]) == 1: # unique
        mappings.put_recursively(list(value[0])[0], list(value[1])[0])
      else: # ambiguous
        ambiguous_mappings.append(value) 

  # FIXME: It appears gumtree's sorting is broken. GreedySubtreeMatcher.java:59
  # def cmp(a: tuple[set[Node], set[Node]], b: tuple[set[Node], set[Node]]):
  #   return (max(a[0], key=lambda x: x.size)) - (max())
        
  for value in ambiguous_mappings:
    for a in value[0]:
      for b in value[1]:
        if not (a in mappings.src_to_dst or b in mappings.dst_to_src):
          mappings.put_recursively(a, b)

  return mappings

class ZsTree:
  def __init__(self, node: Node):
    self.node_count = node.size
    self.leaf_count = 0
    self.llds: list[int] = [0] * self.node_count
    self.labels: list[Node] = [None] * self.node_count

    idx: int = 1
    tmp_data: dict[Node, int] = {}
    for n in node.postorder():
      if n is None: break

      tmp_data[n] = idx
      self.labels[idx-1] = n
      
      leaf = n
      while len(leaf.children) != 0: 
        leaf = leaf.children[0]

      self.llds[idx-1] = tmp_data[leaf]-1
      if len(n.children) == 0:
        self.leaf_count += 1

      idx += 1

    # set_key_roots
    
    self.key_roots: list[int] = [0] * (self.leaf_count + 1)
    visited: list[bool] = [False] * (self.node_count + 1)
    k = len(self.key_roots) - 1

    i = self.node_count
    while i >= 1:
      if not visited[self.lld(i)]:
        self.key_roots[k] = i
        visited[self.lld(i)] = True
        k -= 1
      i -= 1

  def lld(self, i):
    return self.llds[i-1] + 1
  
  def tree(self, i):
    return self.labels[i-1]

    
# NOTE: I hate this one.
def match_optimal_zs(mappings: MappingDict, src: Node, dst: Node):
  # FIXME: This whole thing...
  zs_src = ZsTree(src)
  zs_dst = ZsTree(dst)

  tree_dist   = [ [0]*(zs_dst.node_count+1) for i in range(zs_src.node_count+1)]
  forest_dist = [ [0]*(zs_dst.node_count+1) for i in range(zs_src.node_count+1)]

  def get_update_cost(a: Node, b: Node):
    if a.type != b.type:
      return sys.float_info.max
    
    if a.label == "" or b.label == "":
      return 1.0
    
    return normalized_tri_gram_distance(a.label, b.label)

  def compute_forest_dist(i: int, j: int):
    forest_dist[zs_src.lld(i) - 1][zs_dst.lld(j) - 1] = 0

    di = zs_src.lld(i)
    while di <= i:
        cost_del = 1.0
        forest_dist[di][zs_dst.lld(j) - 1] = forest_dist[di - 1][zs_dst.lld(j) - 1] + cost_del
        
        dj = zs_dst.lld(j)
        while dj <= j:
            cost_ins = 1.0
            forest_dist[zs_src.lld(i) - 1][dj] = forest_dist[zs_src.lld(i) - 1][dj - 1] + cost_ins

            if ((zs_src.lld(di) == zs_src.lld(i) and (zs_dst.lld(dj) == zs_dst.lld(j)))):
                cost_upd = get_update_cost(zs_src.tree(di), zs_dst.tree(dj))
                forest_dist[di][dj] = min(
                        min(forest_dist[di - 1][dj] + cost_del, forest_dist[di][dj - 1] + cost_ins),
                        forest_dist[di - 1][dj - 1] + cost_upd)
                tree_dist[di][dj] = forest_dist[di][dj]
            else:
                forest_dist[di][dj] = min(
                        min(forest_dist[di - 1][dj] + cost_del, forest_dist[di][dj - 1] + cost_ins),
                        forest_dist[zs_src.lld(di) - 1][zs_dst.lld(dj) - 1] + tree_dist[di][dj])
            
            dj += 1
        di += 1

  for i in range(1, len(zs_src.key_roots)):
    for j in range(1, len(zs_dst.key_roots)):
      compute_forest_dist(zs_src.key_roots[i], zs_dst.key_roots[j])


  root_node_pair = True
  tree_pairs: list[tuple[int, int]] = []
  tree_pairs.append((zs_src.node_count, zs_dst.node_count))

  while len(tree_pairs) > 0:
    last_row, last_col = tree_pairs.pop(0)

    if not root_node_pair:
      compute_forest_dist(last_row, last_col)

    root_node_pair = False

    first_row, first_col = zs_src.lld(last_row) - 1, zs_dst.lld(last_col) - 1
    
    row, col = last_row, last_col
    while (row > first_row) and (col > first_col):
      if ((row > first_row) and (forest_dist[row - 1][col] + 1.0 == forest_dist[row][col])):
          row -= 1
      elif ((col > first_col) and (forest_dist[row][col - 1] + 1.0 == forest_dist[row][col])):
          col -= 1
      else:
        if ((zs_src.lld(row) - 1 == zs_src.lld(last_row) - 1) \
            and (zs_dst.lld(col) - 1 == zs_dst.lld(last_col) - 1)):
          t_src: Node = zs_src.tree(row)
          t_dst: Node = zs_dst.tree(col)
          if (t_src.type == t_dst.type):
            mappings.put(t_src, t_dst)
          else:
            raise Exception("Should not map incompatible nodes.")
          row -= 1
          col -= 1
        else:
          tree_pairs.insert(0, (row, col))

          row = zs_src.lld(row) - 1
          col = zs_dst.lld(col) - 1

  return mappings


def match_greedy_bottom_up(mappings: MappingDict, src: Node, dst: Node):
  SIM_THRESHOLD = 0.5
  SIZE_THRESHOLD = 1000

  def last_chance_match(a: Node, b: Node):
    if a.size >= SIZE_THRESHOLD and b.size >= SIZE_THRESHOLD: return

    zs_mappings = MappingDict()
    match_optimal_zs(mappings, a, b)

    for src_cand, dst_cand in zs_mappings.src_to_dst:
      if mappings.is_mapping_allowed(src_cand, dst_cand):
        mappings.put(src_cand, dst_cand)

  def get_dst_candidates(a: Node):
    seeds: list[Node] = []
    candidates: list[Node] = []
    visited: set[Node] = set()

    for node in a.preorder():
      if node is a: continue
      if node is None: break

      if node in mappings.src_to_dst:
        seeds.append(mappings.src_to_dst[node])

    for seed in seeds:
      while seed.parent is not None:
        parent = seed.parent
        if parent in visited: break
        visited.add(parent)
        if parent.type == a.type and not (parent in mappings.dst_to_src or parent.parent is None):
          candidates.append(parent)
        seed = parent

    return candidates

  for node in src.postorder():
    if node is None: break

    if node.parent is None:
      mappings.put(node, dst)
      last_chance_match(node, dst)
      break

    if len(node.children) == 0 or node in mappings.src_to_dst:
      continue

    candidates: list[Node] = get_dst_candidates(node)
    best: Optional[Node] = None
    the_max: float = -1.0

    for candidate in candidates:
      sim = dice_similarity(mappings, node, candidate)
      if sim > the_max and sim >= SIM_THRESHOLD:
        the_max = sim
        best = candidate

    if best is not None:
      last_chance_match(node, best)
      mappings.put(node, best)

  return mappings

# TODO: Make stateless. Don't like that each function modifies the `mappings`
# variable, but can't figure out a performant way to do it.
def generate_mappings(
  src: Node, dst: Node, 
  funcs: list[MatchingFunc] = [match_greedy_subtree, match_greedy_bottom_up]
):
  mappings = MappingDict()
  for f in funcs:
    f(mappings, src, dst)

  return mappings