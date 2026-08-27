# Bayesian Network Editor (CLI)

A command-line tool for building custom Bayesian Networks: define nodes,
their possible states, the dependencies (edges) between them, and their
Conditional Probability Tables (CPTs) - then run exact probabilistic
inference queries against the network. Networks can be saved to and loaded
from JSON files.

## Design: Model-View-Controller

```
BayesianNetworkEditor/
├── main.py                            # entry point - wires Model, View, Controller together
├── Model/
│   ├── node.py                        # Node: a single variable, its states & CPT
│   ├── network.py                     # BayesianNetwork: nodes + edges (DAG), validation, save/load
│   └── inference.py                   # exact inference (enumeration-ask algorithm)
├── View/
│   └── cli_view.py                    # ALL print()/input() calls live here
├── Controller/
│   └── controller.py                  # main loop; translates menu choices into
│                                      # model calls + view calls
├── Examples/
    ├── 50-Node_Complex_Network.json   # 50-node network (CPT table not set)
    ├── alarm_network.json             # classic "Burglary/Earthquake/Alarm" example (AIMA)
│   └── subgraph_network.json          # network made up of 10 5-node networks
│
└── Graphics/
    ├── 50-Node_Complex_Network.svg    # graphic of a 50-node network
    ├── Alarm_Network.svg              # graphic of the "Burglary/Earthquake/Alarm" example
    └── Subgraph_Network               # graphic of 10 5-node networks
```

- **Model** (`Model/`): pure Python, no I/O. `Node` holds a variable's
  states and CPT rows. `BayesianNetwork` owns the collection of nodes,
  enforces the DAG structure (no cycles, no dangling edges), validates
  completeness, and serializes to/from JSON. `inference.py` implements the
  enumeration-ask exact inference algorithm on top of the model.
- **View** (`View/cli_view.py`): every `print()` and `input()` in the app.
  It only deals with plain data (strings, lists, dicts) handed to it by the
  Controller - it has no knowledge of `Node`/`BayesianNetwork` classes.
- **Controller** (`Controller/controller.py`): the glue. Runs the main
  menu loop, calls View methods to collect input, calls Model methods to
  mutate/query state, and calls View methods again to display results or
  errors. This is the only layer that imports both Model and View.

This separation means you could swap `CLIView` for a GUI or web view later
without touching `Model/` at all.

## Running it

```bash
cd BayesianNetworkEditor
python3 main.py
```

## Usage
Below are the available commands in command line
Use help [command] to get usage information for each command
Commands are case-insensitive 'add node', Add Node', and ADD NODE'
all work
```
Commands:
  Help                Displays commands and what they do
  Rename Network      Renames the network
  Add Node            Adds a new node to the network
  Remove Node         Removes a node from the network
  Rename Node         Renames a node from the network
  Add Edge            Designates a parent-child relationship between nodes
  Remove Edge         Removes a parent-child relationship
  Define CPT          Set probability of states for a node
  Show Network        Show the structure of the network
  Show Node           Show details of one node
  Check Network       Validate the network
  Query               Run an inference query
  Save                Save network as a json file
  Load                Loads a network from a json file
  New                 Starts a new network
  Export              Exports network as a graphic (SVG)
  Quit/Exit           Exits the program
  ```


### Typical workflow

1. **Add nodes** - give each a name and comma-separated states,
   e.g. name `Rain`, states `Yes,No`.
2. **Add dependencies** - e.g. parent `Rain`, child `Umbrella`
   means Umbrella's probability depends on Rain. Cycles are rejected.
3. **Define CPTs** - for each node, you'll be walked through
   every combination of its parents' states and asked for a probability
   per state of the node itself (must sum to 1.0). Root nodes (no parents)
   just need one row - their prior.
4. **Validate** - checks the network is a DAG and every node
   has a complete CPT.
5. **Query** - pick a variable to ask about, optionally enter
   evidence (known values) for other variables, and get back the exact
   posterior distribution.
6. **Save / Load** - persist your network as JSON, or load
   one back later (including the bundled example).
7. **Export a diagram** - draws the current network as boxes
   and arrows and saves it as an `.svg` file under `./Graphics/`.
8. **Rename** things anytime - the network itself or an
   individual node. Renaming a node updates every edge that
   references it and preserves its CPT and position in listings.

### Try the bundled example

From the `BayesianNetworkEditor` directory, enter the load command and then enter:

```
Examples/alarm_network.json
```

This loads the classic "Burglary / Earthquake / Alarm / JohnCalls /
MaryCalls" network. Try querying `Burglary` with evidence
`JohnCalls=True, MaryCalls=True` - you should get ≈ 0.2842, matching the
textbook result.

## File format

Saved networks are plain JSON:

```json
{
  "name": "Alarm Network (classic AIMA example)",
  "nodes": [
    {
      "name": "Burglary",
      "states": ["True", "False"],
      "parents": [],
      "cpt": { "": [0.001, 0.999] }
    },
    {
      "name": "Alarm",
      "states": ["True", "False"],
      "parents": ["Burglary", "Earthquake"],
      "cpt": {
        "True|True": [0.95, 0.05],
        "True|False": [0.94, 0.06],
        "False|True": [0.29, 0.71],
        "False|False": [0.001, 0.999]
      }
    }
  ]
}
```

CPT keys are parent-state combinations joined with `|` (in the order of
that node's `parents` list); the value is the probability of each of the
node's own `states`, in order. A root node's only key is the empty string.

## Inference algorithm

Queries are answered exactly using **enumeration-ask**: for the query
variable, each of its possible states is combined with the given evidence,
and all remaining (hidden) variables are summed out in topological order
using the chain rule of the network. This is exact (not sampling-based),
which is appropriate for the small/medium hand-built networks this tool
targets.

## Graphic export

Option 15 renders the current network to a standalone `.svg` file under
`./Graphics/` (created automatically). Nodes are laid out in layers -
level 0 for root nodes (no parents), and each other node one level below
the deepest of its parents - with arrows drawn from each parent down to
its children. Box width adapts to the node name's length.

This is pure Python string-building (no matplotlib/graphviz/networkx
dependency), so the output opens in any browser or vector image viewer
with nothing extra to install. Nodes are exported in the network's
topological order (parents before children) regardless of the order
they were originally added in, since layering depends on a parent's
level being known before its children's.

## Extending

- Add a new View (e.g. a `WebView` or `GUIView`) implementing the same
  method names as `CLIView`, and pass it into `BayesianNetworkController`
  - no changes to `model/` needed.
- Swap `inference.py`'s algorithm for variable elimination or sampling
  (e.g. rejection/likelihood-weighting) if networks grow large - the
  Controller only calls `query(network, var, evidence)`, so the interface
  stays stable.
