import itertools
import sys
from collections import defaultdict
from typing import Callable, Optional

from sequoia_diff.models import MappingDict, Node, NodePriorityQueue
from sequoia_diff.string_comparisons import normalized_tri_gram_distance

MatchingFunc = Callable[[MappingDict, Node, Node], MappingDict]


def number_of_mapped_descendants(mappings: MappingDict, src: Node, dst: Node):
    dst_descendants: set[Node] = set()
    for node in dst.pre_order(skip_self=True):
        dst_descendants.add(node)

    mapped_descendants: int = 0

    for node in src.pre_order(skip_self=True):
        if node not in mappings.src_to_dst:
            continue

        dst_for_src_descendant = mappings.src_to_dst[node]
        if dst_for_src_descendant in dst_descendants:
            mapped_descendants += 1

    return mapped_descendants


def dice_similarity(mappings: MappingDict, src: Node, dst: Node) -> float:
    common = number_of_mapped_descendants(mappings, src, dst)
    return 2.0 * common / (src.size + dst.size)


def match_greedy_top_down(mappings: MappingDict, src: Node, dst: Node):
    """
    Map the common subtrees of src and dst with the greatest height possible.
    """

    ambiguous_mappings: list[tuple[set[Node], set[Node]]] = []

    pq_src = NodePriorityQueue()
    pq_dst = NodePriorityQueue()

    pq_src.push(src)
    pq_dst.push(dst)

    # Find trees with the same height
    while pq_src.synchronize_and_push_children(pq_dst):
        _, src_nodes = pq_src.pop_equal_priority()
        _, dst_nodes = pq_dst.pop_equal_priority()

        local_mappings: dict[int, tuple[set[Node], set[Node]]] = defaultdict(
            lambda: (set(), set())
        )

        # Utilize the hash function to determine of two nodes are isomorphic
        for node in src_nodes:
            local_mappings[hash(node)][0].add(node)
        for node in dst_nodes:
            local_mappings[hash(node)][1].add(node)

        for _, local_set in local_mappings.items():
            src_set, dst_set = local_set

            # Unmapped
            if len(src_set) == 0 or len(dst_set) == 0:
                for node in src_set:
                    pq_src.push_children(node)
                for node in dst_set:
                    pq_dst.push_children(node)
                pass

            # Unique
            elif len(src_set) == 1 and len(dst_set) == 1:
                mappings.put_recursively(list(src_set)[0], list(dst_set)[0])

            # Ambiguous
            else:
                ambiguous_mappings.append(local_set)

    # TODO: Implement dice similarity sorting, something like:
    #   cmp = lambda a, b: dice(*b) - dice(*a)
    #   key = functools.cmp_to_key(cmp)
    #   sorted_product = sorted(itertools.product(src_set, dst_set), key=key)

    for src_set, dst_set in ambiguous_mappings:
        for a, b in itertools.product(src_set, dst_set):
            if not (a in mappings.src_to_dst or b in mappings.dst_to_src):
                mappings.put_recursively(a, b)

    return mappings


class RTEDTree:
    """
    https://arxiv.org/pdf/1201.0230

    TODO: Clean up and implement APTED algorithm
    https://github.com/DatabaseGroup/apted
    """

    def __init__(self, node: Node):
        self.node_count = node.size
        self.leaf_count = 0
        self.leftmost_leaf_desc: list[int] = [0] * self.node_count
        self.labels: list[Optional[Node]] = [None] * self.node_count

        idx: int = 1
        tmp_data: dict[Node, int] = {}
        for n in node.post_order():
            tmp_data[n] = idx
            self.labels[idx - 1] = n

            leaf = n
            while len(leaf.children) != 0:
                leaf = leaf.children[0]

            self.leftmost_leaf_desc[idx - 1] = tmp_data[leaf] - 1
            if len(n.children) == 0:
                self.leaf_count += 1

            idx += 1

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
        return self.leftmost_leaf_desc[i - 1] + 1

    def tree(self, i):
        return self.labels[i - 1]


def match_rted(mappings: MappingDict, src: Node, dst: Node):
    """
    https://arxiv.org/pdf/1201.0230

    TODO: Clean up and implement APTED algorithm
    https://github.com/DatabaseGroup/apted
    """
    zs_src = RTEDTree(src)
    zs_dst = RTEDTree(dst)

    tree_dist = [[0] * (zs_dst.node_count + 1) for i in range(zs_src.node_count + 1)]
    forest_dist = [[0] * (zs_dst.node_count + 1) for i in range(zs_src.node_count + 1)]

    def get_update_cost(a: Node, b: Node):
        if a.type != b.type:
            return sys.float_info.max

        return normalized_tri_gram_distance(a.label, b.label)

    def compute_forest_dist(i: int, j: int):
        forest_dist[zs_src.lld(i) - 1][zs_dst.lld(j) - 1] = 0

        di = zs_src.lld(i)
        while di <= i:
            cost_del = 1.0
            forest_dist[di][zs_dst.lld(j) - 1] = (
                forest_dist[di - 1][zs_dst.lld(j) - 1] + cost_del
            )

            dj = zs_dst.lld(j)
            while dj <= j:
                cost_ins = 1.0
                forest_dist[zs_src.lld(i) - 1][dj] = (
                    forest_dist[zs_src.lld(i) - 1][dj - 1] + cost_ins
                )

                if zs_src.lld(di) == zs_src.lld(i) and (
                    zs_dst.lld(dj) == zs_dst.lld(j)
                ):
                    cost_upd = get_update_cost(zs_src.tree(di), zs_dst.tree(dj))
                    forest_dist[di][dj] = min(
                        min(
                            forest_dist[di - 1][dj] + cost_del,
                            forest_dist[di][dj - 1] + cost_ins,
                        ),
                        forest_dist[di - 1][dj - 1] + cost_upd,
                    )
                    tree_dist[di][dj] = forest_dist[di][dj]
                else:
                    forest_dist[di][dj] = min(
                        min(
                            forest_dist[di - 1][dj] + cost_del,
                            forest_dist[di][dj - 1] + cost_ins,
                        ),
                        forest_dist[zs_src.lld(di) - 1][zs_dst.lld(dj) - 1]
                        + tree_dist[di][dj],
                    )

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
            if (row > first_row) and (
                forest_dist[row - 1][col] + 1.0 == forest_dist[row][col]
            ):
                row -= 1
            elif (col > first_col) and (
                forest_dist[row][col - 1] + 1.0 == forest_dist[row][col]
            ):
                col -= 1
            else:
                if (zs_src.lld(row) - 1 == zs_src.lld(last_row) - 1) and (
                    zs_dst.lld(col) - 1 == zs_dst.lld(last_col) - 1
                ):
                    t_src: Node = zs_src.tree(row)
                    t_dst: Node = zs_dst.tree(col)
                    if t_src.type == t_dst.type:
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


def match_last_chance(mappings: MappingDict, a: Node, b: Node):
    SIZE_THRESHOLD = 1000
    if a.size >= SIZE_THRESHOLD and b.size >= SIZE_THRESHOLD:
        return

    zs_mappings = MappingDict()
    match_rted(zs_mappings, a, b)

    for src_cand, dst_cand in zs_mappings.src_to_dst.items():
        if mappings.is_mapping_allowed(src_cand, dst_cand):
            mappings.put(src_cand, dst_cand)


def get_dst_candidates(mappings: MappingDict, a: Node):
    seeds: list[Node] = []
    candidates: list[Node] = []
    visited: set[Node] = set()

    for node in a.pre_order(skip_self=True):
        if node in mappings.src_to_dst:
            seeds.append(mappings.src_to_dst[node])

    for seed in seeds:
        while seed.parent is not None:
            parent = seed.parent
            if parent in visited:
                break
            visited.add(parent)
            if parent.type == a.type and not (
                parent in mappings.dst_to_src or parent.parent is None
            ):
                candidates.append(parent)
            seed = parent

    return candidates


def match_greedy_bottom_up(mappings: MappingDict, src: Node, dst: Node):
    SIM_THRESHOLD = 0.5

    for node in src.post_order():
        if node.parent is None:
            mappings.put(node, dst)
            match_last_chance(mappings, node, dst)
            break

        if len(node.children) == 0 or node in mappings.src_to_dst:
            continue

        best: Optional[Node] = None
        the_max: float = -1.0
        for candidate in get_dst_candidates(mappings, node):
            sim = dice_similarity(mappings, node, candidate)
            if sim > the_max and sim >= SIM_THRESHOLD:
                the_max = sim
                best = candidate

        if best is not None:
            match_last_chance(mappings, node, best)
            mappings.put(node, best)

    return mappings


def match_chawathe_fast(mappings: MappingDict, src: Node, dst: Node):
    """
    S. S. Chawathe, A. Rajaraman, H. Garcia-Molina, and J. Widom. Change
    detection in hierarchically structured information. In Proceedings of the
    1996 International Conference on Management of Data, pages 493–504. ACM
    Press, 1996.

    1. M <- phi
    2. For each leaf label l do
        a. S1 <- chain_T1(l)
        b. S2 <- chain_T2(l)
        c. lcs <- LCS(S1, S2, equal)
        d. For each pair (x, y) in lcs, add (x, y) to M
        e. For each unmatched node x in S1, if there is an unmatched node y in
           S2 such that equal(x, y) then
            i. Add (x, y) to M
            ii. Mark x and y "matched"
    3. Repeat steps 2a-2e for each internal node label l.
    """

    raise NotImplementedError()


def generate_mappings(
    src: Node,
    dst: Node,
    funcs: list[MatchingFunc] | None = None,
):
    """
    Establish mappings between similar nodes of the two trees.

    There are only two constraints for these mappings:
    - A given node can only belong to one mapping.
    - Mappings involve two nodes with identical types.
    """

    if funcs is None:
        funcs = [match_greedy_top_down, match_greedy_bottom_up]

    mappings = MappingDict()
    for f in funcs:
        f(mappings, src, dst)

    return mappings
