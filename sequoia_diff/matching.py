import itertools
import sys
from collections import defaultdict
from typing import Callable, NoReturn, Optional

from sequoia_diff.models import MappingDict, Node, NodePriorityQueue
from sequoia_diff.string_comparisons import normalized_tri_gram_distance

MatchingFunc = Callable[[MappingDict, Node, Node], None]


def number_of_mapped_descendants(mappings: MappingDict, src: Node, dst: Node) -> int:
    """
    Returns the number of descendants of src that are mapped to descendants of
    dst.
    """
    dst_descendants = set(node for node in dst.pre_order(skip_self=True))

    result = 0
    for node in src.pre_order(skip_self=True):
        if mappings.src_to_dst.get(node) in dst_descendants:
            result += 1

    return result


def dice_similarity(mappings: MappingDict, src: Node, dst: Node) -> float:
    """
    The Dice similarity coefficient is a statistic used to gauge the similarity
    between two samples. Originally defined as `2*|A ∩ B| / (|A| + |B|)`.

    https://en.wikipedia.org/wiki/Dice-S%C3%B8rensen_coefficient
    """
    common = number_of_mapped_descendants(mappings, src, dst)
    return float(2.0 * common / (src.size + dst.size))


def match_greedy_top_down(mappings: MappingDict, src: Node, dst: Node) -> None:
    """
    Map the common subtrees of src and dst with the greatest height possible.

    https://dl.acm.org/doi/10.1145/2642937.2642982
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
            local_mappings[node.subtree_hash_value][0].add(node)
        for node in dst_nodes:
            local_mappings[node.subtree_hash_value][1].add(node)

        for _, local_set in local_mappings.items():
            src_set, dst_set = local_set

            # Unmapped
            if len(src_set) == 0 or len(dst_set) == 0:
                for node in src_set:
                    pq_src.push_children(node)
                for node in dst_set:
                    pq_dst.push_children(node)

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


class RTEDTree:
    """
    Data structure for use in the RTED algorithm. It mainly takes care of
    finding the leftmost leaf descendants of each node.

    https://arxiv.org/abs/1201.0230

    TODO: Clean up (lots of weird 1-indexed stuff) and implement APTED algorithm
    """

    def __init__(self, node: Node):
        self.size = node.size
        self.leaf_count = 0
        self.leftmost_leaf_descendant: list[int] = [0] * self.size
        self.nodes = [n for n in node.post_order()]

        node_to_idx: dict[Node, int] = {}
        for idx, n in enumerate(node.post_order(), 1):
            node_to_idx[n] = idx
            self.nodes[idx - 1] = n

            leaf = n
            while len(leaf.children) != 0:
                leaf = leaf.children[0]

            self.leftmost_leaf_descendant[idx - 1] = node_to_idx[leaf] - 1
            if len(n.children) == 0:
                self.leaf_count += 1

        self.key_roots: list[int] = [0] * (self.leaf_count + 1)
        visited: list[bool] = [False] * (self.size + 1)
        j = len(self.key_roots) - 1

        for i in range(self.size, 0, -1):
            if not visited[self.lld(i)]:
                self.key_roots[j] = i
                visited[self.lld(i)] = True
                j -= 1

    def lld(self, i: int) -> int:
        return self.leftmost_leaf_descendant[i - 1] + 1

    def tree(self, i: int) -> Node:
        return self.nodes[i - 1]


def match_rted(mappings: MappingDict, src: Node, dst: Node) -> MappingDict:
    """
    RTED algorithm for tree edit distance.

    https://arxiv.org/abs/1201.0230

    TODO: Clean up (lots of weird 1-indexed stuff) and implement APTED algorithm
    """
    zs_src = RTEDTree(src)
    zs_dst = RTEDTree(dst)

    tree_dist = [[0.0] * (zs_dst.size + 1) for _ in range(zs_src.size + 1)]
    forest_dist = [[0.0] * (zs_dst.size + 1) for _ in range(zs_src.size + 1)]

    def get_update_cost(a: Node, b: Node) -> float:
        if a.type != b.type:
            return sys.float_info.max

        return normalized_tri_gram_distance(a.label, b.label)

    def compute_forest_dist(i: int, j: int) -> None:
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
    tree_pairs.append((zs_src.size, zs_dst.size))

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


def match_last_chance(mappings: MappingDict, a: Node, b: Node) -> None:
    """
    Use the RTED algorithm to match the remaining nodes. Technically, any
    matching algorithm that does not produce Move edit actions will work.

    The best known algorithm with add, delete and update actions has a O(n^3)
    time complexity with n being the number of nodes of the AST [1]. Computing
    the minimum edit script that can include move node actions is known to be
    NP-hard [2].

    [1]: https://arxiv.org/abs/1201.0230
    [2]: https://doi.org/10.1016/j.tcs.2004.12.030
    """
    SIZE_THRESHOLD = 1000
    if a.size >= SIZE_THRESHOLD and b.size >= SIZE_THRESHOLD:
        return

    zs_mappings = MappingDict()
    match_rted(zs_mappings, a, b)

    for src_cand, dst_cand in zs_mappings.items():
        if mappings.is_mapping_allowed(src_cand, dst_cand):
            mappings.put(src_cand, dst_cand)


def get_dst_candidates(mappings: MappingDict, src: Node) -> list[Node]:
    """
    Get dst candidates. Look for dst nodes that are already mapped and then
    recursively look at their parents. They become a candidate if:
    - Have the same type as src
    - Are not the root node
    - Are not already mapped
    """
    dst_seeds: list[Node] = []
    for node in src.pre_order(skip_self=True):
        if node in mappings.src_to_dst:
            dst_seeds.append(mappings.src_to_dst[node])

    candidates: list[Node] = []
    visited: set[Node] = set()

    for dst_seed in dst_seeds:
        while dst_seed.parent is not None:
            parent = dst_seed.parent
            if parent in visited:
                break

            visited.add(parent)
            if parent.type == src.type and not (
                parent.parent is None or parent in mappings.dst_to_src
            ):
                candidates.append(parent)

            dst_seed = parent

    return candidates


def match_greedy_bottom_up(mappings: MappingDict, src: Node, dst: Node) -> None:
    """
    https://dl.acm.org/doi/10.1145/2642937.2642982
    """
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


def match_chawathe_fast(mappings: MappingDict, src: Node, dst: Node) -> NoReturn:
    """
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

    https://dl.acm.org/doi/10.1145/235968.233366
    """

    raise NotImplementedError()


# TODO: Add the ability to pass in kwargs to the matching functions.
def generate_mappings(
    src: Node,
    dst: Node,
    funcs: list[MatchingFunc] | None = None,
) -> MappingDict:
    """
    Establish mappings between similar nodes of the two trees.

    There are only two constraints for these mappings:
    - A given node can only belong to one mapping.
    - Mappings involve two nodes with identical types.
    """

    if funcs is None:
        funcs = [match_greedy_top_down, match_greedy_bottom_up]

    mappings = MappingDict()
    for func in funcs:
        func(mappings, src, dst)

    return mappings
