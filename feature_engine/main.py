import argparse
import dash

from pathlib import Path
from feature_engine.model import FeatureContainer


def main():
    parser = argparse.ArgumentParser(prog='feature_engine', description='Feature Engineering Toolchain')
    parser.add_argument('-i', '--input', help='input', type=str, required=True)

    args = parser.parse_args()

    FC = FeatureContainer.from_yaml(Path(args.input), debug=True)

    app = dash.Dash(__name__, title="Feature Engine")
    app.layout = FC.cytoscape()
    app.run_server(debug=True)


if __name__ == "__main__":
    main()
