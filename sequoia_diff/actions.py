from collections import defaultdict
from typing import Callable, TypeVar, cast

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


def find_pos(dst_node: Node, dst_in_order: set[Node], mappings: MappingDict):
    parent = dst_node.parent
    if parent is None:
        return 0

    siblings = parent.children

    # If x is the leftmost child of its parent that is marked "in order", return
    # 0
    for sibling in siblings:
        if sibling in dst_in_order:
            if sibling is dst_node:

                return 0
            break

    # Find the rightmost sibling of x that is to the left of x and is marked "in
    # order"
    rightmost_in_order_sibling: Node | None = None
    for i in range(dst_node.position_in_parent):
        sibling = siblings[i]
        if sibling in dst_in_order:
            rightmost_in_order_sibling = sibling

    if rightmost_in_order_sibling is None:
        return 0

    u = mappings.dst_to_src[rightmost_in_order_sibling]
    return u.position_in_parent + 1


def align_children(
    partner_node: Node,
    current_node: Node,
    src_in_order: set[Node],
    dst_in_order: set[Node],
    cpy_mappings: MappingDict,
    cpy_to_src: dict[Node, Node],
) -> list[Action]:
    """
    Statefully modify the tree and return a list of actions.
    """

    actions: list[Action] = []

    # Mark all children of current_node and partner_node as "out of order"
    for c in partner_node.children:
        if c in src_in_order:
            src_in_order.remove(c)
    for c in current_node.children:
        if c in dst_in_order:
            dst_in_order.remove(c)

    # Children of partner_node whose partners are children of current_node
    matched_partner_children: list[Node] = []
    for c in partner_node.children:
        if (
            c in cpy_mappings.src_to_dst
            and cpy_mappings.src_to_dst[c] in current_node.children
        ):
            matched_partner_children.append(c)

    # Children of current_node whose partners are children of partner_node
    matched_current_children: list[Node] = []
    for c in current_node.children:
        if (
            c in cpy_mappings.dst_to_src
            and cpy_mappings.dst_to_src[c] in partner_node.children
        ):
            matched_current_children.append(c)

    lcs_list = lcs(
        matched_partner_children,
        matched_current_children,
        lambda a, b: a == cpy_mappings.dst_to_src[b],
    )

    for m in lcs_list:
        src_in_order.add(m[0])
        dst_in_order.add(m[1])

    # Ensure left-to-right insertions by doing s2 first
    for c in matched_current_children:
        for p in matched_partner_children:
            if not cpy_mappings.has(p, c):
                continue
            if (p, c) in lcs_list:
                continue

            # Append and apply move operation

            # NOTE: Shouldn't happen
            if p.parent is None:
                raise ValueError("parent is None")

            partner_node.children.remove(p)
            position = find_pos(c, dst_in_order, cpy_mappings)
            actions.append(Move(cpy_to_src[p], cpy_to_src[partner_node], position))
            partner_node.children.insert(position, p)

            src_in_order.add(p)
            dst_in_order.add(c)

    return actions


def generate_chawathe_edit_script(mappings: MappingDict, src: Node, dst: Node):
    """
    Perform the Chawathe algorithm to generate an edit script.

    https://doi.org/10.1145/235968.233366
    """

    # Create a copy of src to work with. We could technically create a copy of
    # dst, but we never modify it (aside from setting a fake parent), so it's
    # not necessary.
    cpy_src = src.deep_copy()
    cpy_mappings = MappingDict()

    def fake_node():
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
        parent_partner: Node = cpy_mappings.dst_to_src[cast(Node, current_node.parent)]
        partner_node: Node

        # If current node has no partner
        if current_node not in cpy_mappings.dst_to_src:
            partner_node = fake_node()
            position = find_pos(current_node, dst_in_order, cpy_mappings)

            actions.append(Insert(current_node, cpy_to_src[parent_partner], position))

            cpy_to_src[partner_node] = current_node
            cpy_mappings.put(partner_node, current_node)
            parent_partner.children.insert(position, partner_node)

        # else if current_node is not the root
        elif current_node is not dst:
            partner_node = cpy_mappings.dst_to_src[current_node]

            if partner_node.parent is None:  # Should not happen
                raise ValueError("parent is None")
            v = partner_node.parent

            if partner_node.label != current_node.label:
                # Append and apply update operation
                actions.append(
                    Update(
                        cpy_to_src[partner_node],
                        cpy_to_src[partner_node].label,
                        current_node.label if current_node.label else "",
                    )
                )
                partner_node.label = current_node.label

            if parent_partner is not v:
                # Append and apply move operation
                position = find_pos(current_node, dst_in_order, cpy_mappings)
                actions.append(
                    Move(cpy_to_src[partner_node], cpy_to_src[parent_partner], position)
                )

                old_position = partner_node.position_in_parent
                partner_node.parent.children.pop(old_position)
                parent_partner.children.insert(position, partner_node)
        else:
            partner_node = cpy_mappings.dst_to_src[current_node]

        src_in_order.add(partner_node)
        dst_in_order.add(current_node)

        align_children_actions = align_children(
            partner_node,
            current_node,
            src_in_order,
            dst_in_order,
            cpy_mappings,
            cpy_to_src,
        )

        actions.extend(align_children_actions)

    for node in cpy_src.post_order():
        if node.type == "fake-type":
            continue
        if node not in cpy_mappings.src_to_dst:
            actions.append(Delete(cpy_to_src[node]))

    dst.set_parent(dst_orig_parent)  # Restore dst.parent

    return actions


def generate_simplified_chawathe_edit_script(
    mappings: MappingDict, src: Node, dst: Node
):
    actions = generate_chawathe_edit_script(mappings, src, dst)

    added_nodes: dict[Node, Insert] = {}
    deleted_nodes: dict[Node, Delete] = {}

    for action in actions:
        if isinstance(action, Insert):
            added_nodes[action.node] = action
        elif isinstance(action, Delete):
            deleted_nodes[action.node] = action

    for n in added_nodes:
        if n.parent in added_nodes and all(
            d in added_nodes for d in n.parent.pre_order(skip_self=True)
        ):
            actions.remove(added_nodes[n])

        # elif len(n.children) > 0 and all(d in added_nodes for d in n.parent.pre_order(skip_self=True)):
        #   orig_action = added_nodes[n]
        #   # FIXME: actually insert-tree

    for n in deleted_nodes:
        if n.parent in deleted_nodes and all(
            d in deleted_nodes for d in n.parent.pre_order(skip_self=True)
        ):
            actions.remove(deleted_nodes[n])

        # if t.parent in added_trees and all(descendant in added_trees for descendant in t.parent.descendants):
        #     actions.remove(added_trees[t])

    return actions
