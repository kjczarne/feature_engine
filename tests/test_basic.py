import unittest

from pathlib import Path

from feature_engine.model import FeatureContainer, Feature, BindingTime, Relationship, RelationshipTypes


class TestBasic(unittest.TestCase):

    def test_basic_load_and_compare(self):
        FC = FeatureContainer(features=[
            Feature(0, "Feature 1", BindingTime.COMPILATION, "Rationale 1", True, [Relationship(1, RelationshipTypes.ALTERNATIVE)]),
            Feature(1, "Feature 2", BindingTime.COMPILATION, "Rationale 2", True, []),
        ])

        FC_from_yaml = FeatureContainer.from_yaml(
            Path(__file__).parent / "res" / "basic.yaml",
            debug=True
        )

        self.assertEqual(FC, FC_from_yaml)


if __name__ == "__main__":
    unittest.main()
