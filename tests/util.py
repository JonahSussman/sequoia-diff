import os
from io import TextIOWrapper
from typing import ItemsView, cast

import tree_sitter_java
from tree_sitter import Language, Parser

from sequoia_diff.models import Action, Delete, Insert, MappingDict, Move, Node, Update

PATH_TESTS = os.path.dirname(os.path.abspath(__file__))

PATH_DATA = os.path.join(PATH_TESTS, "data")

TS_LANGUAGE_JAVA = Language(tree_sitter_java.language())


def read_and_parse_tree(
    parser_or_language: Language | Parser, file_path: str | TextIOWrapper
):
    if isinstance(parser_or_language, Parser):
        parser = parser_or_language
    elif isinstance(parser_or_language, Language):
        parser = Parser(parser_or_language)
    else:
        raise ValueError(
            f"parser_or_language must be of type Parser or Language, not {type(parser_or_language)}"
        )

    if isinstance(file_path, TextIOWrapper):
        file_contents = file_path.read()
    else:
        with open(file_path, "r") as f:
            file_contents = f.read()

    tree = parser.parse(bytes(file_contents, "utf-8"))

    return tree


# TODO: Evaluate just using the regular Node constructor and supply label or
# type if one is missing.
def node(label_and_type: str, **kwargs):
    return Node(label=label_and_type, type=label_and_type, **kwargs)


# TODO: Determine if this should be a method of Action or a standalone function.
def dictize_action(action: Action):
    obj: dict
    if isinstance(action, Insert):
        obj = {
            "kind": "insert_node",
            "node": action.node.pretty_str_self(),
            "parent": action.parent.pretty_str_self(),
            "pos": action.pos,
            "whole_subtree": action.whole_subtree,
        }
    elif isinstance(action, Delete):
        obj = {
            "kind": "delete_node",
            "node": action.node.pretty_str_self(),
        }
    elif isinstance(action, Move):
        obj = {
            "kind": "move_node",
            "node": action.node.pretty_str_self(),
            "parent": action.parent.pretty_str_self(),
            "pos": action.pos,
        }
    elif isinstance(action, Update):
        obj = {
            "kind": "update_node",
            "node": action.node.pretty_str_self(),
            "old_label": action.old_label,
            "new_label": action.new_label,
        }
    else:
        raise ValueError(f"Unknown action type: {type(action)}")

    return obj


def dictize_mappings(mappings: MappingDict):
    for a, b in mappings.items():
        yield {
            "src": a.pretty_str_self(),
            "dst": b.pretty_str_self(),
        }


def dictize_mapping(mapping: ItemsView[Node, Node]):
    return {
        "src": cast(Node, mapping[0]).pretty_str_self(),
        "dst": cast(Node, mapping[1]).pretty_str_self(),
    }
