import os
import unittest

import yaml

from sequoia_diff.models import LanguageRuleSet


class TestLineMatch(unittest.TestCase):
    def test_load_rules(self):
        script_dir = os.path.dirname(__file__)
        rules_file = os.path.join(script_dir, "rules.yaml")

        with open(rules_file, "r") as f:
            LanguageRuleSet.model_validate(yaml.safe_load(f))
