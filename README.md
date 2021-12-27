# Feature Engine

Feature Engine is an experimental graph-based feature engineering tool that reads a declarative description of feature requirements from a YAML file and presents the requirements as a graph.

## Usage

1. Clone this repo.
2. `cd` into this repo and run `pip install -e .` to install the project in development mode. At the moment we don't provide any wheels until we reach the first version of the stable API.
3. Run `feature_engine -i path/to/some.yaml`.

### Writing the YAML feature representations

```yaml
version: '0.1'
features:
- binding_time: compilation
  guid: 0
  is_mandatory: true
  name: Feature 1
  rationale: Rationale 1
  relationships:
    - guid: 1
      rel: complex
```

The example above outlines the format used with `feature_engine`:

- `version` -> API version corresponding to the version of the application itself
- `features` -> a list of `Feature` objects
    - `binding_time` -> `compilation`, `initialization` or `runtime`. Denotes at what stage of the software production process should the feature be implemented.
    - `guid` -> globally unique identifier. Every feature should have a unique GUID. It should always be a monotonically rising integer.
    - `is_mandatory` -> if `true` the feature is a mandatory element of the implemented software.
    - `name` -> human-readable name of the feature.
    - `rationale` -> description explaining the rationale of the feature.
    - `relationships` -> a list of `Relationship` objects
        - `guid` -> GUID of the feature to which a relationship is being formed.
        - `rel` -> relationship type. Can be `alternative`, `incompatible` or `complex` at the moment.

### Graph compilation

The graph is compiled when the application is started. Compilation process verifies that a set of rules is met by the graph in question. For example, you should never have two features that are listed as mandatory and are at the same time incompatible. We attempt to catch such invalid states.

There are two types of rules that we use at the moment:

- Graph Rules -> decorated with the `feature_engine.model.graph_rule` decorator. These are rules that pertain to the entire graph, for example _no two nodes can have the same GUID_.
- Edge Rules -> decorated with the `feature_engine.model.edge_rule` decorator. These are rules that pertain to the particular feature-to-feature relationships, e.g. _no two obligatory features can be listed as incompatible_.
