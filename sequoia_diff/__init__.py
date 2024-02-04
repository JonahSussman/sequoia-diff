import os
import yaml
from collections import defaultdict

from tree_sitter import Tree

from sequoia_diff.types import Rules, Node, MappingDict, Action
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

  # print('mappings:')
  # for a, b in mappings.src_to_dst.items():
  #   print(f"{a.pretty_str_self()} <-> {b.pretty_str_self()}")
  # print()

  from sequoia_diff.types import Insert, Update, Move, Delete
  # print('actions:')
#   for action in edit_script:
#     if isinstance(action, Insert):
#       print(f"""{action.name}
#   - insert: {action.node.pretty_str_self()}
#   - to: {action.parent.pretty_str_self()}""")
#     elif isinstance(action, Update):
#       print(f"""{action.name}
# - replace: {action.node.label}
# - by: {action.value}""")
#     elif isinstance(action, Move):
#       pass
#     elif isinstance(action, Delete):
#       pass

  for e in edit_script:
    e.node = e.node.ts_node
    if isinstance(e, Insert) or isinstance(e, Move):
      e.parent = e.parent.ts_node

  import tree_sitter as ts
  def s(a: ts.Node):
    if a is None: return "None"
    return f"{a.type} [{a.start_byte}, {a.end_byte}]"

  for a in edit_script:
      if isinstance(a, Insert):
        print(f"""{a.name}
- node: {s(a.node)}
- parent: {s(a.parent)}
- pos: {a.pos}""")
      elif isinstance(a, Update):
        print(f"""{a.name}
- node: {s(a.node)}
- label: {a.label}
- value: {a.value}""")
      elif isinstance(a, Move):
        print(f"""{a.name}
- node: {s(a.node)}
- parent: {s(a.parent)}
- pos: {a.pos}""")
      elif isinstance(a, Delete):
        print(f"""{a.name}
- node: {s(a.node)}""")

  # TODO: return actual tree_sitter nodes
  return edit_script
