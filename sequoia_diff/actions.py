from collections import defaultdict

from sequoia_diff.types import MappingDict, Node
from sequoia_diff.types import Action, Insert, Update, Move, Delete

def fake_node(*children: Node):
  start_byte = 0
  end_byte   = float('inf')
  size       = 0
  height     = 0
  hash_value = 0
  structure_hash_value = 0

  for c in children:
    start_byte = min(start_byte, c.start_byte)
    end_byte = max(end_byte, c.end_byte)
    size += c.size
    height = max(height, c.height + 1)
    hash_value += c.hash_value
    structure_hash_value += c.structure_hash_value

  return Node(
    ts_node=None,
    type="fake-type",
    start_byte=start_byte,
    end_byte=end_byte,
    label="",
    children=list(children),
    parent=None,
    size=size,
    height=height,
    hash_value=hash(hash_value + hash('fake-type') + hash('')),
    structure_hash_value=hash(structure_hash_value + hash('fake-type'))
  )


def generate_chawathe_edit_script(mappings: MappingDict, src: Node, dst: Node):
  cpy_src = src.deep_copy()
  cpy_mappings = MappingDict()

  # src_to_cpy, cpy_to_src = {}, {}
  src_to_cpy = defaultdict(lambda: fake_node())
  cpy_to_src = defaultdict(lambda: fake_node())
  src_gen, cpy_gen = src.preorder(), cpy_src.preorder()

  while True:
    src_node, cpy_node = next(src_gen), next(cpy_gen)
    if src_node is None or cpy_node is None: break
    src_to_cpy[src_node] = cpy_node
    cpy_to_src[cpy_node] = src_node

  for src_node, dst_node in mappings.src_to_dst.items():
    cpy_mappings.put(src_to_cpy[src_node], dst_node)

  src_fake_root, dst_fake_root = fake_node(cpy_src), fake_node(dst)

  cpy_src.parent = src_fake_root

  dst_orig_parent = dst.parent
  dst.parent = dst_fake_root

  actions: list[Action] = []
  dst_in_order: set[Node] = set()
  src_in_order: set[Node] = set()

  cpy_mappings.put(src_fake_root, dst_fake_root)


  def find_pos(x: Node):
    y = x.parent
    siblings = y.children

    for c in siblings:
      if c in dst_in_order:
        if c is x:
          return 0
        break

    v: Node | None = None
    for i in range(x.position_in_parent()):
      c = siblings[i]
      if c in dst_in_order:
        v = c

    if v is None: return 0

    u = cpy_mappings.dst_to_src[v]
    return u.position_in_parent() + 1

  def lcs(x: list[Node], y: list[Node]):
    m, n = len(x), len(y)
    result: list[tuple[Node, Node]] = []
    
    opt = [[0 for _ in range(n + 1)] for _ in range(m + 1)]

    for i in range(m - 1, -1, -1):
      for j in range(n - 1, -1, -1):
        if cpy_mappings.dst_to_src[y[j]] == x[i]:
          opt[i][j] = opt[i + 1][j + 1] + 1
        else:
          opt[i][j] = max(opt[i + 1][j], opt[i][j + 1])

    i, j = 0, 0
    while i < m and j < n:
      if cpy_mappings.dst_to_src[y[j]] == x[i]:
        result.append((x[i], y[j]))
        i += 1
        j += 1
      elif opt[i+1][j] >= opt[i][j+1]:
        i += 1
      else:
        j += 1

    return result

  for x in dst.bfs():
    if x is None: break

    w: Node = None
    y: Node = x.parent
    z: Node = cpy_mappings.dst_to_src[y]

    if x not in cpy_mappings.dst_to_src:
      k = find_pos(x)
      w = fake_node()
      actions.append(Insert(x, cpy_to_src[z], k))
      cpy_to_src[w] = x
      cpy_mappings.put(w, x)
      z.children.insert(k, w)
    else:
      w = cpy_mappings.dst_to_src[x]
      if x is not dst:
        v = w.parent
        if w.label != x.label:
          actions.append(Update(cpy_to_src[w], cpy_to_src[w].label, x.label))
          w.label = x.label
        if z is not v:
          k = find_pos(x)
          actions.append(Move(cpy_to_src[w], cpy_to_src[z], k))
          old_k = w.position_in_parent()
          w.parent.children.pop(old_k)
          z.children.insert(k, w)


    src_in_order.add(w)
    dst_in_order.add(x)

    # align_children

    for c in w.children:
      if c in src_in_order: src_in_order.remove(c)
    for c in x.children: 
      if c in dst_in_order: dst_in_order.remove(c)

    s1: list[Node] = []
    s2: list[Node] = []

    for c in w.children:
      if c in cpy_mappings.src_to_dst:
        if cpy_mappings.src_to_dst[c] in x.children:
          s1.append(c)

    for c in x.children:
      if c in cpy_mappings.dst_to_src:
        if cpy_mappings.dst_to_src[c] in w.children:
          s2.append(c)

    lcs_list = lcs(s1, s2)

    for m in lcs_list:
      src_in_order.add(m[0])
      dst_in_order.add(m[1])

    for b in s2: 
      for a in s1:
        if not cpy_mappings.has(a, b): continue
        if (a, b) in lcs_list: continue
        a.parent.children.remove(a)
        k = find_pos(b)
        actions.append(Move(cpy_to_src[a], cpy_to_src[w], k))
        w.children.insert(k, a)
        a.parent = w
        src_in_order.add(a)
        dst_in_order.add(b)

  for w in cpy_src.postorder():
    if w is None: break
    if w.type == 'fake-type': continue
    if w not in cpy_mappings.src_to_dst:
      actions.append(Delete(cpy_to_src[w]))

  dst.parent = dst_orig_parent

  return actions


def generate_simplified_chawathe_edit_script(mappings: MappingDict, src: Node, dst: Node):
  actions = generate_chawathe_edit_script(mappings, src, dst)

  added_nodes: dict[Node, Insert] = {}
  deleted_nodes: dict[Node, Delete] = {}

  for a in actions:
    if isinstance(a, Insert):
      added_nodes[a.node] = a
    elif isinstance(a, Delete):
      deleted_nodes[a.node] = a

  # FIXME: Add to Node class
  def desc(node: Node):
    result: list[Node] = []
    for n in node.preorder():
      if n is None: break
      if n is node: continue
      result.append(n)
    return result


  for n in added_nodes:
    if n.parent in added_nodes and all(d in added_nodes for d in desc(n.parent)):
      actions.remove(added_nodes[n])
    # elif len(n.children) > 0 and all(d in added_nodes for d in desc(n.parent)):
    #   orig_action = added_nodes[n]
    #   # FIXME: actually insert-tree
      
  for n in deleted_nodes:
    if n.parent in deleted_nodes and all(d in deleted_nodes for d in desc(n.parent)):
      actions.remove(deleted_nodes[n])

    # if t.parent in added_trees and all(descendant in added_trees for descendant in t.parent.descendants):
    #     actions.remove(added_trees[t])

  return actions