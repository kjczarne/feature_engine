import unittest
from pathlib import Path
from feature_engine.model import FeatureContainer, CompileException


class TestInvalidGraphs(unittest.TestCase):

    def fixture(self, filename: str):
        FC = FeatureContainer.from_yaml(
            Path(__file__).parent / "res" / filename,
            debug=True
        )
        with self.assertRaises(CompileException):
            FC.compile()

    def test_invalid_conflicting_relationships(self):
        self.fixture("invalid_conflicting_relationships.yaml")

    def test_mutually_exclusive_obligatory_relationships(self):
        self.fixture("invalid_mutually_exclusive_obligatory.yaml")


if __name__ == "__main__":
    unittest.main()
