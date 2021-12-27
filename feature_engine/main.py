import argparse
import dash
import json
from ruamel import yaml
from io import StringIO
from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State

from pathlib import Path
from feature_engine.model import FeatureContainer


def create_app(input_file_path: Path):
    FC = FeatureContainer.from_yaml(input_file_path, debug=True)

    app = dash.Dash(__name__, title="Feature Engine")
    init_graph = FC.cytoscape()

    styles = {
        'yaml-output': {
            'overflow-y': 'scroll',
            'height': 'calc(50% - 25px)',
            'border': 'thin lightgrey solid'
        },
        'tab': {'height': 'calc(98vh - 80px)'},
        'reload-button': {'width': '100%'},
    }
    app.layout = html.Div(style={"display": "flex"}, children=[
        dcc.Store('reload-clicks'),
        html.Div(id='graph-div', className='eight columns', style={"flex": 5}, children=[
            init_graph
        ]),

        html.Div(className='four columns', style={"height": "100vh", "flex": 5, 'box-sizing': "border-box"}, children=[
            dcc.Tabs(id='tabs', children=[
                dcc.Tab(label='Data', children=[
                    html.Div(
                        # style=styles['tab'],
                        children=[
                            html.P('Node Object YAML:'),
                            html.Pre(
                                id='tap-node-yaml-output',
                                style=styles['yaml-output']
                            ),
                            html.P('Edge Object YAML:'),
                            html.Pre(
                                id='tap-edge-yaml-output',
                                style=styles['yaml-output']
                            )
                        ]
                    )
                ]),
                dcc.Tab(label='Control Panel', children=[
                    html.Button('Reload', id='reload-button', style=styles['reload-button']),
                ])
            ]),
        ])
    ])

    @app.callback(Output('tap-node-yaml-output', 'children'),
                  [Input('cytoscape', 'tapNode')])
    def display_tap_node(data):
        serializer = yaml.YAML(typ="unsafe", pure=True)
        if data is not None:
            feature_matching_guid = list(filter(lambda f: int(data["data"]["id"]) == f.guid, FC.features))
            buffer = StringIO()
            serializer.dump(feature_matching_guid[0].to_dict(), buffer)
            return buffer.getvalue()
        return "null"

    @app.callback(Output('tap-edge-yaml-output', 'children'),
                  [Input('cytoscape', 'tapEdge')])
    def display_tap_edge(data):
        serializer = yaml.YAML(typ="unsafe", pure=True)
        if data is not None:
            feature_matching_guid = list(filter(lambda f: int(data["sourceData"]["id"]) == f.guid, FC.features))
            buffer = StringIO()
            serializer.dump([r.to_dict() for r in feature_matching_guid[0].relationships], buffer)
            return buffer.getvalue()
        return "null"

    @app.callback(
        Output('graph-div', 'children'),
        Output('reload-clicks', 'data'),
        Input('reload-button', 'n_clicks'),
        State('reload-clicks', 'data'),
    )
    def reload_graph(n_clicks, n_clicks_prev):
        if not n_clicks_prev:
            n_clicks_prev = 0
        if n_clicks:
            if n_clicks > n_clicks_prev:
                return [FC.cytoscape()], n_clicks
            n_clicks_prev = n_clicks
        return [init_graph], n_clicks_prev

    return app


def main():
    parser = argparse.ArgumentParser(prog='feature_engine', description='Feature Engineering Toolchain')
    parser.add_argument('-i', '--input', help='input', type=str, required=True)

    args = parser.parse_args()
    app = create_app(Path(args.input))
    app.run_server(debug=True)


if __name__ == "__main__":
    main()
