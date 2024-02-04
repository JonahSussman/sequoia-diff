from dataclasses import dataclass, field

from tree_sitter import Language, Parser

from sequoia_diff import SEQUOIA_RULES
from sequoia_diff.types import Node, MappingDict

TS_OUTPUT_PATH = "tree-sitter-java-build/language-java.so"
TS_REPO_PATHS = ["./tree-sitter-java/"]
TS_NAME = "java"

Language.build_library(TS_OUTPUT_PATH, TS_REPO_PATHS)
TS_JAVA_LANGUAGE = Language(TS_OUTPUT_PATH, TS_NAME)


FILE_PATH_BEFORE  = './ExampleClass.java'
FILE_PATH_AFTER   = './ExampleClassAfterChange.java'

parser = Parser()
parser.set_language(TS_JAVA_LANGUAGE)

with open(FILE_PATH_BEFORE, 'r') as f:
  file_before = f.read()
tree_before = parser.parse(bytes(file_before, 'utf-8'))

with open(FILE_PATH_AFTER, 'r') as f:
  file_after = f.read()
tree_after = parser.parse(bytes(file_after, 'utf-8'))

print(tree_before.root_node.descendant_count)
print(tree_before.root_node.sexp())
print(SEQUOIA_RULES['java'])

node = Node.from_tree_sitter_tree(SEQUOIA_RULES['java'], tree_before)
print(node.pretty_str())

# ---

node_b = node.children[0]
m = MappingDict()
m.put(node, node_b)
print((id(node), id(node_b)))
for e in set(m):
  print(f"{id(e[0]), id(e[1])}")

# ---

@dataclass
class Nodeish:
  field: str

  def __hash__(self): 
    return hash(str(self))

@dataclass
class Dictish:
  mapping: dict[Nodeish, Nodeish] = field(default_factory=dict)

  def copy(self):
    return Dictish(mapping=dict(self.mapping))


nodeish_a = Nodeish('nodeish_a')
nodeish_b = Nodeish('nodeish_b')

dictish_a = Dictish()
dictish_a.mapping[nodeish_a] = nodeish_b

dictish_b = dictish_a.copy()

for key, value in dictish_a.mapping.items(): print((hex(id(key)), hex(id(value))))
for key, value in dictish_b.mapping.items(): print((hex(id(key)), hex(id(value))))

# print(dict(None))

from queue import PriorityQueue

pq = PriorityQueue()

pq.put((3, "!"))
pq.put((2, "world"))
pq.put((1, "hello"))

while not pq.empty():
  print(pq.queue[0])
  pq.get()

# --- 

# changed_class_body = tree_before.root_node.named_children[1].child_by_field_name('body')
# field_a = changed_class_body.named_children[0]
# field_b = changed_class_body.named_children[1]
# node_field_a = Node.from_tree_sitter_node(SEQUOIA_RULES['java'], field_a)
# node_field_b = Node.from_tree_sitter_node(SEQUOIA_RULES['java'], field_b)
# print(node_field_a.pretty_str())
# print(node_field_b.pretty_str())
# assert hash(node_field_a) == hash(node_field_b)
# node_field_dict = {}
# node_field_dict[hash(node_field_a)] = 'hello!'
# print(node_field_dict[hash(node_field_b)])

# import heapq
# print(heapq.heappop([]))

# ---

from sequoia_diff.matching import generate_mappings
x = generate_mappings(
  Node.from_tree_sitter_tree(SEQUOIA_RULES['java'], tree_before), 
  Node.from_tree_sitter_tree(SEQUOIA_RULES['java'], tree_after)
)

for a, b in x.dst_to_src.items():
  print(f"{a.type} [{a.start_byte}, {a.end_byte}] <-> {b.type} [{b.start_byte}, {b.end_byte}]")

from typing import NamedTuple

@dataclass
class SumA: 
  hello: str; yo: str

@dataclass
class SumB:
  world: str

SumAB = SumA | SumB

def switch_on_type(sum: SumAB):
  if   isinstance(sum, SumA):
    print(sum.yo)
  elif isinstance(sum, SumB):
    print(sum.world)
  else:
    print("lmao")

switch_on_type(SumA("hello", 'yo'))
switch_on_type(SumB("world"))

def test_variadic_args(*stuff: str):
  for item in stuff:
    print(item)

test_variadic_args('one', 'two', 'three')

# ---

from sequoia_diff import get_tree_diff
from sequoia_diff.types import Action, Insert, Update, Move, Delete

actions = get_tree_diff('java', tree_before, tree_after)

import tree_sitter as ts

def s(a: ts.Node):
  if a is None: return "None"
  return f"{a.type} [{a.start_byte}, {a.end_byte}]"

for a in actions:
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