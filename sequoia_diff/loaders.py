import json
import os
from typing import Callable, Optional

import tree_sitter as ts

from sequoia_diff.models import LanguageRules, LanguageRuleSet, Node

LoaderFunc = Callable[..., Node]

PATH_TS_RULES = os.path.join(os.path.dirname(__file__), "rules.json")


def from_tree_sitter_node(
    ts_node: ts.Node, language_or_rules: Optional[LanguageRules | str] = None
) -> Node:
    if language_or_rules is None:
        rules = LanguageRules()
    elif isinstance(language_or_rules, str):
        language = language_or_rules

        with open(PATH_TS_RULES, "r") as f:
            rule_set = LanguageRuleSet.model_validate(json.loads(f.read()))

        root_rules = rule_set.root.get(language)
        if root_rules is None:
            raise ValueError(f"Language '{language}' not supported")
        rules = root_rules
    else:  # isinstance(language_or_rules, LanguageRules)
        rules = language_or_rules

    if ((ts_node.child_count == 0) or (ts_node.type in rules.flattened)) and (
        ts_node.text is not None
    ):
        label = ts_node.text.decode("utf-8")
    else:
        label = None

    output = Node(
        orig_node=ts_node,
        type=rules.aliased.get(ts_node.type, ts_node.type),
        label=label,
    )

    if ts_node.type not in rules.flattened:
        for ts_child in ts_node.children:
            if ts_child.type in rules.ignored:
                continue

            output_child = from_tree_sitter_node(ts_child, rules)
            output.children_append(output_child)

    return output


def from_tree_sitter_tree(
    tree: ts.Tree, language_or_rules: Optional[LanguageRules | str] = None
) -> Node:
    return from_tree_sitter_node(tree.root_node, language_or_rules)
