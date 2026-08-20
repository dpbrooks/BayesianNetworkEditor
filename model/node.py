"""
model/node.py
 
Defines the Node class: a single random variable in a Bayesian Network.
 
A Node has:
    - a name (unique identifier)
    - a finite list of discrete states (e.g. ["True", "False"])
    - a list of parent node names (its dependencies)
    - a Conditional Probability Table (CPT)
 
The CPT is stored as a dict:
    { (parent_state_1, parent_state_2, ...): [p(state_0), p(state_1), ...] }
 
For a root node (no parents) the only key is the empty tuple `()`.
The order of values in each probability row matches the order of `states`.
The order of values in each key tuple matches the order of `parents`.
"""
 
import itertools
 
 
class CPTError(Exception):
    """Raised when a CPT row is invalid (wrong length, doesn't sum to 1, etc.)."""
    pass
 
 
class Node:
    def __init__(self, name, states, parents=None, cpt=None):
        if not name or not isinstance(name, str):
            raise ValueError("Node name must be a non-empty string.")
        if not states or len(states) < 2:
            raise ValueError(f"Node '{name}' needs at least 2 states.")
        if len(set(states)) != len(states):
            raise ValueError(f"Node '{name}' has duplicate state names.")
 
        self.name = name
        self.states = list(states)
        self.parents = list(parents) if parents else []
        # cpt keys are tuples of parent-state strings; values are lists of floats
        self.cpt = dict(cpt) if cpt else {}
 
    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------
    def set_name(self, new_name):
        if not new_name or not isinstance(new_name, str):
            raise ValueError("Node name must be a non-empty string.")
        self.name = new_name
 
    # ------------------------------------------------------------------
    # Parent / structure management
    # ------------------------------------------------------------------
    def set_parents(self, parents):
        """Replace the parent list. Clears the CPT since row shape changes."""
        self.parents = list(parents)
        self.cpt = {}
 
    def all_parent_combinations(self, network):
        """
        Return every possible combination of parent states, as a list of tuples,
        in an order consistent with self.parents. `network` is used to look up
        each parent's Node object for its states.
        """
        if not self.parents:
            return [()]
        parent_state_lists = [network.get_node(p).states for p in self.parents]
        return list(itertools.product(*parent_state_lists))
 
    # ------------------------------------------------------------------
    # CPT management
    # ------------------------------------------------------------------
    def set_cpt_row(self, parent_values, probabilities, tolerance=1e-3):
        """
        Set one row of the CPT.
 
        parent_values: tuple of parent state values, in the order of self.parents
                        (empty tuple if this node has no parents)
        probabilities: list of floats, one per state in self.states, must sum to 1
        """
        parent_values = tuple(parent_values)
        if len(parent_values) != len(self.parents):
            raise CPTError(
                f"Expected {len(self.parents)} parent value(s) for node "
                f"'{self.name}', got {len(parent_values)}."
            )
        if len(probabilities) != len(self.states):
            raise CPTError(
                f"Expected {len(self.states)} probabilities for node "
                f"'{self.name}' (states: {self.states}), got {len(probabilities)}."
            )
        for p in probabilities:
            if p < 0 or p > 1:
                raise CPTError(f"Probabilities must be between 0 and 1 (got {p}).")
        total = sum(probabilities)
        if abs(total - 1.0) > tolerance:
            raise CPTError(
                f"Probabilities for node '{self.name}' with parents={parent_values} "
                f"sum to {total:.4f}, not 1.0."
            )
        self.cpt[parent_values] = [float(p) for p in probabilities]
 
    def is_fully_specified(self, network):
        """True if every combination of parent states has a CPT row defined."""
        for combo in self.all_parent_combinations(network):
            if combo not in self.cpt:
                return False
        return True
 
    def missing_rows(self, network):
        """List parent-value combinations that still need a CPT row."""
        return [c for c in self.all_parent_combinations(network) if c not in self.cpt]
 
    def probability(self, value, evidence):
        """
        Return P(self.name = value | parents=evidence values).
        `evidence` is a dict mapping variable name -> state value, and must
        contain an entry for every parent of this node.
        """
        if value not in self.states:
            raise ValueError(f"'{value}' is not a valid state of node '{self.name}'.")
        key = tuple(evidence[p] for p in self.parents)
        if key not in self.cpt:
            raise CPTError(
                f"No CPT row defined for node '{self.name}' with parent values {key}."
            )
        idx = self.states.index(value)
        return self.cpt[key][idx]
 
    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self):
        # JSON object keys must be strings, so tuples are joined with "|"
        cpt_serializable = {
            ("|".join(k) if k else ""): v for k, v in self.cpt.items()
        }
        return {
            "name": self.name,
            "states": self.states,
            "parents": self.parents,
            "cpt": cpt_serializable,
        }
 
    @staticmethod
    def from_dict(data):
        cpt = {}
        for k, v in data.get("cpt", {}).items():
            key_tuple = tuple(k.split("|")) if k != "" else ()
            cpt[key_tuple] = v
        return Node(
            name=data["name"],
            states=data["states"],
            parents=data.get("parents", []),
            cpt=cpt,
        )
 
    def __repr__(self):
        return f"Node(name={self.name!r}, states={self.states}, parents={self.parents})"
 