import argparse
import yaml
import dash
import networkx as nx

from typing import Generator
from feature_engine.model import FeatureContainer, Feature, Relationship, RelationshipTypes, Direction, DirectionalRelationship, BindingTime

def main():
    # parser = argparse.ArgumentParser(prog='feature_engine', description='Feature Engineering Toolchain')
    # parser.add_argument('-i', '--input', help='input', type=str)
    # parser.add_argument('-o', '--output', help='output', type=str)

    # args = parser.parse_args()

    # G = nx.Graph()

    # nx.draw_networkx(G)
    
    FC = FeatureContainer(features=[
        Feature(0, "Feature 1", BindingTime.COMPILATION, "Rationale 1", True, [Relationship(1, RelationshipTypes.ALTERNATIVE)]),
        Feature(1, "Feature 2", BindingTime.COMPILATION, "Rationale 2", True, []),
    ])
    
    FC.to_yaml("test.yaml")
    G = FC.to_nx_graph()
    
    FC2 = FeatureContainer.from_yaml("test2.yaml")
    G2 = FC2.to_nx_graph()
    print("test")
    
    app = dash.Dash(__name__)
    app.layout = FC2.cytoscape()
    app.run_server(debug=True)


if __name__ == "__main__":
    main()
