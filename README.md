# Bayesian Network Builder (CLI)

A command-line tool for building custom Bayesian Networks: define nodes,
their possible states, the dependencies (edges) between them, and their
Conditional Probability Tables (CPTs) - then run exact probabilistic
inference queries against the network. Networks can be saved to and loaded
from JSON files.

## Design: Model-View-Controller

```
bn_cli/
├── main.py                      # entry point - wires Model, View, Controller together
├── model/
│   ├── node.py                  # Node: a single variable, its states & CPT
│   ├── network.py               # BayesianNetwork: nodes + edges (DAG), validation, save/load
│   └── inference.py             # exact inference (enumeration-ask algorithm)
├── view/
│   └── cli_view.py               # ALL print()/input() calls live here
├── controller/
│   └── controller.py             # main loop; translates menu choices into
│                                  # model calls + view calls
└── examples/
    └── alarm_network.json        # classic "Burglary/Earthquake/Alarm" example (AIMA)
```

- **Model** (`model/`): pure Python, no I/O. `Node` holds a variable's
  states and CPT rows. `BayesianNetwork` owns the collection of nodes,
  enforces the DAG structure (no cycles, no dangling edges), validates
  completeness, and serializes to/from JSON. `inference.py` implements the
  enumeration-ask exact inference algorithm on top of the model.
- **View** (`view/cli_view.py`): every `print()` and `input()` in the app.
  It only deals with plain data (strings, lists, dicts) handed to it by the
  Controller - it has no knowledge of `Node`/`BayesianNetwork` classes.
- **Controller** (`controller/controller.py`): the glue. Runs the main
  menu loop, calls View methods to collect input, calls Model methods to
  mutate/query state, and calls View methods again to display results or
  errors. This is the only layer that imports both Model and View.

This separation means you could swap `CLIView` for a GUI or web view later
without touching `model/` at all.

## Running it

```bash
cd bn_cli
python3 main.py
```

## Usage
Below are the available commands in command line
Use help [command] to get usage information for each command
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
  Quit                Exits the program
  ```


### Typical workflow

1. **Add nodes** (option 1) - give each a name and comma-separated states,
   e.g. name `Rain`, states `Yes,No`.
2. **Add dependencies** (option 3) - e.g. parent `Rain`, child `Umbrella`
   means Umbrella's probability depends on Rain. Cycles are rejected.
3. **Define CPTs** (option 5) - for each node, you'll be walked through
   every combination of its parents' states and asked for a probability
   per state of the node itself (must sum to 1.0). Root nodes (no parents)
   just need one row - their prior.
4. **Validate** (option 8) - checks the network is a DAG and every node has
   a complete CPT.
5. **Query** (option 9) - pick a variable to ask about, optionally enter
   evidence (known values) for other variables, and get back the exact
   posterior distribution.
6. **Save / Load** (options 10/11) - persist your network as JSON, or load
   one back later (including the bundled example).

### Try the bundled example

From the `bn_cli` directory, choose option 11 and enter:

```
examples/alarm_network.json
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

## Extending

- Add a new View (e.g. a `WebView` or `GUIView`) implementing the same
  method names as `CLIView`, and pass it into `BayesianNetworkController`
  - no changes to `model/` needed.
- Swap `inference.py`'s algorithm for variable elimination or sampling
  (e.g. rejection/likelihood-weighting) if networks grow large - the
  Controller only calls `query(network, var, evidence)`, so the interface
  stays stable.
