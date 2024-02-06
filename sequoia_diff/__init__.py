import os
import yaml
from collections import defaultdict

from tree_sitter import Tree

from sequoia_diff.types import Rules, Node, MappingDict, Action
from sequoia_diff.types import Insert, Update, Move, Delete
from sequoia_diff.matching import generate_mappings
from sequoia_diff.actions import generate_simplified_chawathe_edit_script

SEQUOIA_RULES = defaultdict(
  lambda: Rules([], {}, [])
)

def setup_module():
  global SEQUOIA_RULES

  script_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
  rules_file = os.path.join(script_dir, "rules.yaml")
  with open(rules_file, 'r') as f:
    rules: dict[str, dict] = yaml.safe_load(f)
  
  for key, value in rules.items():
    SEQUOIA_RULES[key] = Rules(
      flattened=value['flattened'],
      aliased=value['aliased'],
      ignored=value['ignored'],
    )

setup_module()

def get_tree_diff(language: str, old_ts_tree: Tree, new_ts_tree: Tree):
  rules = SEQUOIA_RULES[language]

  src: Node = Node.from_tree_sitter_tree(rules, old_ts_tree)
  dst: Node = Node.from_tree_sitter_tree(rules, new_ts_tree)

  mappings: MappingDict = generate_mappings(src, dst)
  edit_script: list[Action] = generate_simplified_chawathe_edit_script(mappings, src, dst)

  # actual tree_sitter nodes
  for e in edit_script:
    e.node = e.node.ts_node
    if isinstance(e, Insert) or isinstance(e, Move):
      e.parent = e.parent.ts_node

  return edit_script
