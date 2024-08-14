from typing import Any, Optional

from sequoia_diff.actions import generate_simplified_chawathe_edit_script
from sequoia_diff.loaders import LoaderFunc, from_tree_sitter_tree
from sequoia_diff.matching import generate_mappings
from sequoia_diff.models import Action, MappingDict, Node


def get_tree_diff(
    src_tree: Any,
    dst_tree: Any,
    loader: Optional[LoaderFunc] = None,
    loader_args: Optional[list[Any]] = None,
) -> list[Action]:
    """
    Produces the edit script in order to transform src_tree into dst_tree.
    """

    if loader is None:
        if loader_args is not None:
            raise ValueError("loader_args must be None if loader is None")

        loader = from_tree_sitter_tree
        loader_args = ["java"]
    elif loader_args is None:
        loader_args = []

    src = src_tree if isinstance(src_tree, Node) else loader(src_tree, *loader_args)
    dst = dst_tree if isinstance(dst_tree, Node) else loader(dst_tree, *loader_args)

    mappings: MappingDict = generate_mappings(src, dst)
    edit_script: list[Action] = generate_simplified_chawathe_edit_script(
        mappings, src, dst
    )

    return edit_script


__all__ = [
    "get_tree_diff",
]
