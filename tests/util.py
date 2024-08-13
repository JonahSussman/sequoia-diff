import os

import tree_sitter_java
from tree_sitter import Language, Parser

from sequoia_diff.models import Node

PATH_TESTS = os.path.dirname(os.path.abspath(__file__))

PATH_DATA = os.path.join(PATH_TESTS, "data")

TS_LANGUAGE_JAVA = Language(tree_sitter_java.language())


def read_and_parse_tree(parser_or_language: Language | Parser, file_path: str):
    if isinstance(parser_or_language, Parser):
        parser = parser_or_language
    elif isinstance(parser_or_language, Language):
        parser = Parser(parser_or_language)
    else:
        raise ValueError(
            f"parser_or_language must be of type Parser or Language, not {type(parser_or_language)}"
        )

    with open(file_path, "r") as f:
        file_contents = f.read()

    tree = parser.parse(bytes(file_contents, "utf-8"))

    return tree


# TODO: Evaluate just using the regular Node constructor and supply label or
# type if one is missing.
def node(label_and_type: str, **kwargs):
    return Node(label=label_and_type, type=label_and_type, **kwargs)
