from typing import Any, Optional

from sequoia_diff.actions import generate_simplified_chawathe_edit_script
from sequoia_diff.loaders import LoaderFunc, from_tree_sitter_tree
from sequoia_diff.matching import generate_mappings
from sequoia_diff.models import Action, MappingDict, Node


def get_tree_diff(
    old_tree: Any,
    new_tree: Any,
    loader: Optional[LoaderFunc] = None,
    loader_args: Optional[list[Any]] = None,
):
    """
    Produces the edit script in order to transform old_tree into new_tree.
    """

    if loader is None:
        if loader_args is not None:
            raise ValueError("loader_args must be None if loader is None")

        loader = from_tree_sitter_tree
        loader_args = ["java"]
    elif loader_args is None:
        loader_args = []

    src = old_tree if isinstance(old_tree, Node) else loader(old_tree, *loader_args)
    dst = new_tree if isinstance(new_tree, Node) else loader(new_tree, *loader_args)

    mappings: MappingDict = generate_mappings(src, dst)
    edit_script: list[Action] = generate_simplified_chawathe_edit_script(
        mappings, src, dst
    )

    return edit_script


__all__ = [
    "get_tree_diff",
]
