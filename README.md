# sequoia-diff

An awesome tool to work with abstract syntax trees, providing:

- Algorithms to generate mappings between trees to see what nodes exist in the other
- Algorithms to create "edit scripts", or the sequence of actions to transform one tree into the other.

Named after the giant sequoias, this name implies strength, resilience, and the ability to handle large, complex structures, much like managing complex code structures in a diff tool.

- **sequoia** (/sɪˈkwɔɪ.ə/) - Either of two huge coniferous California trees of the bald cypress family that may reach a height of over 300 feet [^1].
- **diff** (/ dɪf /) - An operation that computes and displays the data difference or differences between two files [^2].

## Getting Started

> [!WARNING]
> This project is under _active development_. As a result, things might severely break between versions. Use it at your own risk!

It's recommended that this library be installed in a virtual environment.

```sh
python -m venv .venv
source .venv/bin/activate
pip install sequoia-diff
```

### Nodes

The core data structure of sequoia-diff is the [Node](https://github.com/JonahSussman/sequoia-diff/blob/main/sequoia_diff/models.py#L24). Nodes have a "type" (like structural elements like "if_statement") and a "label" (like text attached to the node).

You can construct Nodes either manually or using loaders like so:

```python
# Building nodes using loaders. For example, the tree_sitter loader

from sequoia_diff.models import Node
from sequoia_diff.loaders import from_tree_sitter_tree
import tree_sitter_java
import tree_sitter as ts

parser = ts.Parser(ts.Language(tree_sitter_java.language()))
ts_tree = parser.parse(b"public class Test { }")
loader_root = from_tree_sitter_tree(ts_tree, "java")

print(loader_root.pretty_str())
"""
Node(type="program", subtree_hash=0xd19e33244ca...)
  Node(type="class_declaration", subtree_hash=0x38bb1992e23...)
    Node(type="modifiers", subtree_hash=0xa89cb5ba69f...)
      Node(type="public", label="public", subtree_hash=0x7c1f47c6fb9...)
    Node(type="class", label="class", subtree_hash=0x53ba79b0932...)
    Node(type="identifier", label="Test", subtree_hash=0x1759f434dde...)
    Node(type="class_body", subtree_hash=0x2e39dfad18f...)
"""
```

```python
# Building nodes manually

from sequoia_diff.models import Node

manual_root = Node(type="root", label=None, children=[
  Node(type="mid_level", label="a"),
  Node(type="mid_level", label="b"),
  Node(type="another_mid_level", label="c"),
])

print(manual_root.pretty_str())
"""
Node(type="root", subtree_hash=0x691693519f9...)
  Node(type="mid_level", label="a", subtree_hash=0xf4c1d8f2e8a...)
  Node(type="mid_level", label="b", subtree_hash=0x1b09b1156a8...)
  Node(type="another_mid_level", label="c", subtree_hash=0x1d6921ca9ee...)
"""
```

You can also modify the Nodes like so:

```python
# Using convenience methods, which correctly set the parent-child relationship
child1 = Node(type="child", label="Child1")
child2 = Node(type="child", label="Child2")

manual_root.children[2].children_append(child2)
manual_root.children_insert(1, child1)
manual_root.children_remove(manual_root.children[1])
manual_root.set_parent(Node(type="new_root", label=None))

# Deep copy the node
copy_of_root = manual_root.parent.deep_copy()

print(copy_of_root.pretty_str())
"""
Node(type="new_root", subtree_hash=0x42e6081b4af...)
  Node(type="root", subtree_hash=0xd33e85a2b21...)
    Node(type="mid_level", label="a", subtree_hash=0xf4c1d8f2e8a...)
    Node(type="mid_level", label="b", subtree_hash=0x1b09b1156a8...)
    Node(type="another_mid_level", label="c", subtree_hash=0xdf4d5ccb84c...)
      Node(type="child", label="Child2", subtree_hash=0x5e4d9f60de3...)
"""
```

### Mappings and Edit Script (Tree Diff)

You can generate mappings between trees to see which Nodes correspond to which between trees. Support for many different algorithms exist, but the default is `match_greedy_top_down` followed by `match_greedy_bottom_up`.

```python
from sequoia_diff import get_tree_diff
from sequoia_diff.matching import generate_mappings
from sequoia_diff.models import Node
from tests.util import dictize_action, dictize_mapping
import yaml

# Building nodes manually
old_root = Node(type="root", label=None, children=[
    Node(type="a", label="a"),
    Node(type="b", label="b", children=[
        Node(type="b-1", label="b-1"),
        Node(type="b-2", label="b-2"),
    ]),
    Node(type="c", label="c", children=[
        Node(type="c-1", label="c-1"),
        Node(type="c-2", label="c-2"),
    ]),
])

new_root = Node(type="root", label=None, children=[
    Node(type="a", label="ayyy", children=[
        Node(type="a-1", label="a-1"),
        Node(type="a-2", label="a-2"),
    ]),
    Node(type="c", label="c", children=[
        Node(type="c-1", label="c-1"),
        Node(type="c-2", label="c-2"),
    ]),
    Node(type="b", label="b", children=[
        Node(type="b-1", label="b-1"),
        Node(type="b-2", label="b-2"),
    ]),
])

mappings = generate_mappings(old_root, new_root)

print(yaml.dump([dictize_mapping(m) for m in mappings]))

actions = get_tree_diff(old_root, new_root)

print(yaml.dump([dictize_action(a) for a in actions]))
```

## Development

Package built with setuptools using a [flat layout](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#flat-layout).

To install all development dependencies, perform:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## References

- Rules.json adapted from [here](https://github.com/GumTreeDiff/tree-sitter-parser/blob/main/rules.yml).
- Diffing trees using the [Chawathe algorithm](https://doi.org/10.1145/235968.233366) and inspiration from the paper [Fine-grained and accurate source code differencing](https://doi.org/10.1145/2642937.2642982).

 <!-- trunk-ignore-begin(markdownlint/MD034) -->

[^1]: https://www.merriam-webster.com/dictionary/sequoia

[^2]: https://www.dictionary.com/browse/diff

 <!-- trunk-ignore-end(markdownlint/MD034) -->
