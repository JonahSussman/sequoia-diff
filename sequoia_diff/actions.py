from collections import defaultdict
from typing import Callable, Optional, TypeVar, cast

from sequoia_diff.models import Action, Delete, Insert, MappingDict, Move, Node, Update

T = TypeVar("T")


def lcs(
    x: list[T], y: list[T], equal: Callable[[T, T], bool] = lambda a, b: a == b
) -> list[tuple[T, T]]:
    """
    Performs the longest common subsequence algorithm on two lists. It returns a
    list of tuples, where each tuple contains the elements that are common to
    both. The reason for this is that a custom equality function can be
    provided, so we must provide both elements that are "equal".
    """
    m, n = len(x), len(y)
    result: list[tuple[T, T]] = []

    opt = [[0 for _ in range(n + 1)] for _ in range(m + 1)]

    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            if equal(x[i], y[j]):
                opt[i][j] = opt[i + 1][j + 1] + 1
            else:
                opt[i][j] = max(opt[i + 1][j], opt[i][j + 1])

    i, j = 0, 0
    while i < m and j < n:
        if equal(x[i], y[j]):
            result.append((x[i], y[j]))
            i += 1
            j += 1
        elif opt[i + 1][j] >= opt[i][j + 1]:
            i += 1
        else:
            j += 1

    return result


def find_pos(dst_node: Node, dst_in_order: set[Node], mappings: MappingDict) -> int:
    """
    Finds the rightmost sibling of node that is to the left of node and is
    marked in order. Returns the position immediately to the right of it.
    """
    parent = dst_node.parent
    if parent is None:
        return 0

    siblings = parent.children

    # If node is the leftmost child of its parent that is marked "in order",
    # return 0
    for sibling in siblings:
        if sibling in dst_in_order:
            if sibling is dst_node:
                return 0
            break

    # Find the rightmost sibling of node that is to the left of node and is
    # marked "in order"
    rightmost_in_order_sibling: Optional[Node] = None
    for i in range(dst_node.position_in_parent):
        sibling = siblings[i]
        if sibling in dst_in_order:
            rightmost_in_order_sibling = sibling

    if rightmost_in_order_sibling is None:
        return 0

    u = mappings.dst_to_src[rightmost_in_order_sibling]
    if u.parent is None:
        return 0

    return u.position_in_parent + 1


def align_children(
    src: Node,
    dst: Node,
    src_in_order: set[Node],
    dst_in_order: set[Node],
    mappings: MappingDict,
) -> list[Move]:
    """
    Statefully align the children of src and dst.

    We say that the children of src and dst are misaligned if src has matched
    children u and v such that u is to the left of v in src's tree but the
    partner of u is to the right of the partner of v in dst's tree. If we find
    that the children are misaligned, we generate Move operations to align the
    children.
    """

    actions: list[Move] = []

    # Mark all children of src and dst as "out of order"
    for child in src.children:
        if child in src_in_order:
            src_in_order.remove(child)
    for child in dst.children:
        if child in dst_in_order:
            dst_in_order.remove(child)

    # Children of src whose partners are children of dst
    matched_src_children: list[Node] = []
    for child in src.children:
        if mappings.src_to_dst.get(child) in dst.children:
            matched_src_children.append(child)

    # Children of dst whose partners are children of src
    matched_dst_children: list[Node] = []
    for child in dst.children:
        if mappings.dst_to_src.get(child) in src.children:
            matched_dst_children.append(child)

    # Find the longest common subsequence of matched_src_children and
    # matched_dst_children. Basically, the aligned children.
    lcs_list = lcs(
        matched_src_children,
        matched_dst_children,
        lambda a, b: a == mappings.dst_to_src[b],
    )

    for src_node, dst_node in lcs_list:
        src_in_order.add(src_node)
        dst_in_order.add(dst_node)

    # Ensure left-to-right insertions by doing matched_dst first
    for dst_child in matched_dst_children:
        for src_child in matched_src_children:
            # Only consider mapped, misaligned children
            if not mappings.has(src_child, dst_child):
                continue
            if (src_child, dst_child) in lcs_list:
                continue

            # Append and apply move operation

            if src_child.parent is None:  # NOTE: Shouldn't happen
                raise ValueError("parent is None")

            src.children_remove(src_child)
            position = find_pos(dst_child, dst_in_order, mappings)

            actions.append(Move(src_child, src, position))
            src.children_insert(position, src_child)

            src_in_order.add(src_child)
            dst_in_order.add(dst_child)

    return actions


def generate_chawathe_edit_script(
    mappings: MappingDict, src: Node, dst: Node
) -> list[Action]:
    """
    Perform the Chawathe algorithm to generate an edit script.

    https://doi.org/10.1145/235968.233366
    """

    # Create a copy of src to work with. We could technically create a copy of
    # dst, but we never modify it (aside from setting a fake parent), so it's
    # not necessary.
    cpy_src = src.deep_copy()
    cpy_mappings = MappingDict()

    def fake_node() -> Node:
        return Node(type="fake-type", label="fake-label")

    # TODO: See if we can use a MappingDict instead
    src_to_cpy: defaultdict[Node, Node] = defaultdict(fake_node)
    cpy_to_src: defaultdict[Node, Node] = defaultdict(fake_node)

    for src_node, cpy_node in zip(src.pre_order(), cpy_src.pre_order()):
        src_to_cpy[src_node] = cpy_node
        cpy_to_src[cpy_node] = src_node

    for src_node, dst_node in mappings.items():
        cpy_mappings.put(src_to_cpy[src_node], dst_node)

    # Create "fake roots" (sentinel nodes) to make things easier
    dst_orig_parent = dst.parent  # Defer dst.parent = dst_orig_parent

    new_cpy_src_parent = fake_node()
    cpy_src.set_parent(new_cpy_src_parent)

    new_dst_parent = fake_node()
    dst.set_parent(new_dst_parent)

    cpy_mappings.put(new_cpy_src_parent, new_dst_parent)

    actions: list[Action] = []
    dst_in_order: set[Node] = set()
    src_in_order: set[Node] = set()

    # Visit the nodes of dst in breadth-first order
    for current_node in dst.bfs():
        # Parent should always have a partner because of bfs traversal
        partner_of_parent: Node = cpy_mappings.dst_to_src[
            cast(Node, current_node.parent)
        ]
        partner_node: Node

        # If current node has no partner
        if current_node not in cpy_mappings.dst_to_src:
            partner_node = fake_node()
            position = find_pos(current_node, dst_in_order, cpy_mappings)

            actions.append(
                Insert(
                    current_node,
                    cpy_to_src[partner_of_parent],
                    position,
                    whole_subtree=len(current_node.children) == 0,
                )
            )

            cpy_to_src[partner_node] = current_node
            cpy_mappings.put(partner_node, current_node)

            # Funky parent stuff to keep cpy_to_src working, as using
            # children_insert will update the subtree_hash
            partner_of_parent.children.insert(position, partner_node)
            partner_node.parent = partner_of_parent

        # else if current_node is not the root
        elif current_node is not dst:
            partner_node = cpy_mappings.dst_to_src[current_node]

            if partner_node.parent is None:  # Should not happen
                raise ValueError("parent is None")
            parent_of_partner = partner_node.parent

            if partner_node.label != current_node.label:
                # Append and apply update operation
                actions.append(
                    Update(
                        cpy_to_src[partner_node],
                        cpy_to_src[partner_node].label,
                        current_node.label,
                    )
                )
                partner_node.label = current_node.label

            # if not cpy_mappings.has(y, v):
            if (
                partner_of_parent.subtree_hash_value
                != parent_of_partner.subtree_hash_value
            ):
                # Append and apply move operation
                position = find_pos(current_node, dst_in_order, cpy_mappings)
                actions.append(
                    Move(
                        cpy_to_src[partner_node],
                        cpy_to_src[partner_of_parent],
                        position,
                    )
                )

                old_position = partner_node.position_in_parent
                partner_node.parent.children.pop(old_position)
                partner_of_parent.children.insert(position, partner_node)
        else:
            partner_node = cpy_mappings.dst_to_src[current_node]

        src_in_order.add(partner_node)
        dst_in_order.add(current_node)

        for move in align_children(
            partner_node,
            current_node,
            src_in_order,
            dst_in_order,
            cpy_mappings,
        ):
            actions.append(
                Move(cpy_to_src[move.node], cpy_to_src[move.parent], move.pos)
            )

    for node in cpy_src.post_order():
        if node.type == "fake-type":
            continue
        if node not in cpy_mappings.src_to_dst:
            actions.append(Delete(cpy_to_src[node]))

    dst.set_parent(dst_orig_parent)  # Restore dst.parent

    return actions


def generate_simplified_chawathe_edit_script(
    mappings: MappingDict, src: Node, dst: Node
) -> list[Action]:
    actions = generate_chawathe_edit_script(mappings, src, dst)
    """
    The regular Chawathe algorithm generates a lot of redundant actions. This
    function simplifies the edit script by collapsing actions. 
    """
    added_nodes: dict[Node, Insert] = {}
    deleted_nodes: dict[Node, Delete] = {}

    for action in actions:
        if isinstance(action, Insert):
            added_nodes[action.node] = action
        elif isinstance(action, Delete):
            deleted_nodes[action.node] = action

    # Determine if the whole subtree should be inserted or removed.
    # NOTE: There might be a faster way of doing this
    for n in added_nodes:
        if n.parent in added_nodes and all(
            d in added_nodes for d in n.parent.pre_order(skip_self=True)
        ):
            actions.remove(added_nodes[n])
            added_nodes[n.parent].whole_subtree = True

    for n in deleted_nodes:
        if n.parent in deleted_nodes and all(
            d in deleted_nodes for d in n.parent.pre_order(skip_self=True)
        ):
            actions.remove(deleted_nodes[n])

    # TODO: Figure out if there is an intelligent way of removing insert-delete
    # pairs. Either by combining them here or modifying the Chawathe algorithm.

    return actions
