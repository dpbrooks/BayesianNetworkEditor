"""
model/network.py
 
Defines BayesianNetwork: a collection of Nodes connected by directed edges,
forming a Directed Acyclic Graph (DAG). Responsible for structural integrity
(no cycles, no dangling edges) and for serialization (save/load as JSON).
 
Pure "Model" layer: no print()/input() calls live here. All feedback is via
return values or exceptions, which the Controller translates for the View.
"""
 
import json
import os
 
from Model.node import Node, CPTError
 
 
class NetworkError(Exception):
    """Raised for structural problems: cycles, missing nodes, duplicate names, etc."""
    pass
 
 
class BayesianNetwork:
    def __init__(self, name="Untitled Network"):
        self.name = name
        self.nodes = {}  # name -> Node, insertion order preserved (dict is ordered)
 
    # ------------------------------------------------------------------
    # Network management
    # ------------------------------------------------------------------
    def set_name(self, new_name):
        self.name = new_name
 
    
    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------
    def add_node(self, name, states):
        if name in self.nodes:
            raise NetworkError(f"A node named '{name}' already exists.")
        self.nodes[name] = Node(name, states)
        return self.nodes[name]
 
    def remove_node(self, name):
        if name not in self.nodes:
            raise NetworkError(f"No node named '{name}'.")
        # Remove it as a parent from any children, clearing their CPTs
        for node in self.nodes.values():
            if name in node.parents:
                node.set_parents([p for p in node.parents if p != name])
        del self.nodes[name]
 
    def rename_node(self, name, new_name):
        if name not in self.nodes:
            raise NetworkError(f"No node named '{name}'.")
        if not new_name:
            raise NetworkError("New node name cannot be empty.")
        if new_name == name:
            raise NetworkError("New name must be different from the current name.")
        if new_name in self.nodes:
            raise NetworkError(f"A node named '{new_name}' already exists.")
 
        node = self.nodes[name]
        try:
            node.set_name(new_name)
        except ValueError as e:
            raise NetworkError(str(e))
 
        # Rekey self.nodes in place so the renamed node keeps its original
        # position - a plain `del` + reassign would move it to the end and
        # break insertion order (which topological_order()'s tie-breaking
        # and the structure display both rely on for stable output).
        self.nodes = {
            (new_name if key == name else key): value
            for key, value in self.nodes.items()
        }
 
        # Repoint every other node's parent list so edges keep working.
        # This mutates `.parents` directly rather than going through
        # set_parents(), which resets the CPT - a rename only changes a
        # label, not the parent order or the shape of the CPT, so the
        # existing CPT rows (keyed by parent *state* values, not names)
        # remain perfectly valid and must be preserved.
        for other in self.nodes.values():
            if name in other.parents:
                other.parents = [new_name if p == name else p for p in other.parents]
 
 
    def get_node(self, name):
        if name not in self.nodes:
            raise NetworkError(f"No node named '{name}'.")
        return self.nodes[name]
 
    def node_names(self):
        return list(self.nodes.keys())
 
    def children_of(self, name):
        return [n.name for n in self.nodes.values() if name in n.parents]
 
    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------
    def add_edge(self, parent_name, child_name):
        if parent_name not in self.nodes:
            raise NetworkError(f"No node named '{parent_name}'.")
        if child_name not in self.nodes:
            raise NetworkError(f"No node named '{child_name}'.")
        if parent_name == child_name:
            raise NetworkError("A node cannot be its own parent.")
        child = self.nodes[child_name]
        if parent_name in child.parents:
            raise NetworkError(f"'{parent_name}' is already a parent of '{child_name}'.")
 
        # tentatively add and check for cycles
        new_parents = child.parents + [parent_name]
        old_parents = child.parents
        old_cpt = child.cpt
        child.parents = new_parents
        if self._has_cycle():
            # revert
            child.parents = old_parents
            child.cpt = old_cpt
            raise NetworkError(
                f"Adding edge '{parent_name}' -> '{child_name}' would create a cycle."
            )
        # structurally valid: clear the CPT since the row-shape changed
        child.cpt = {}
 
    def remove_edge(self, parent_name, child_name):
        if child_name not in self.nodes:
            raise NetworkError(f"No node named '{child_name}'.")
        child = self.nodes[child_name]
        if parent_name not in child.parents:
            raise NetworkError(f"'{parent_name}' is not a parent of '{child_name}'.")
        child.set_parents([p for p in child.parents if p != parent_name])
 
    def _has_cycle(self):
        """Standard DFS cycle detection over the current parent->child graph."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {name: WHITE for name in self.nodes}
 
        def visit(name):
            color[name] = GRAY
            for child_name in self.children_of(name):
                if color[child_name] == GRAY:
                    return True
                if color[child_name] == WHITE and visit(child_name):
                    return True
            color[name] = BLACK
            return False
 
        for name in self.nodes:
            if color[name] == WHITE:
                if visit(name):
                    return True
        return False
 
    # ------------------------------------------------------------------
    # CPT management (delegates to Node, but validates parent references first)
    # ------------------------------------------------------------------
    def set_cpt_row(self, node_name, parent_values, probabilities):
        node = self.get_node(node_name)
        try:
            node.set_cpt_row(parent_values, probabilities)
        except CPTError as e:
            raise NetworkError(str(e))
 
    # ------------------------------------------------------------------
    # Topological order (needed for inference / display)
    # ------------------------------------------------------------------
    def topological_order(self):
        """Kahn's algorithm. Raises NetworkError if a cycle exists."""
        in_degree = {name: len(node.parents) for name, node in self.nodes.items()}
        queue = [name for name, deg in in_degree.items() if deg == 0]
        order = []
        # sort for deterministic output
        queue.sort()
        while queue:
            queue.sort()
            current = queue.pop(0)
            order.append(current)
            for child_name in self.children_of(current):
                in_degree[child_name] -= 1
                if in_degree[child_name] == 0:
                    queue.append(child_name)
        if len(order) != len(self.nodes):
            raise NetworkError("The network contains a cycle and is not a valid DAG.")
        return order
 
    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self):
        """
        Returns a list of human-readable problem strings. Empty list = valid,
        fully-specified network ready for inference.
        """
        problems = []
        if not self.nodes:
            problems.append("The network has no nodes.")
            return problems
        try:
            self.topological_order()
        except NetworkError as e:
            problems.append(str(e))
        for node in self.nodes.values():
            for parent in node.parents:
                if parent not in self.nodes:
                    problems.append(
                        f"Node '{node.name}' references missing parent '{parent}'."
                    )
            missing = node.missing_rows(self)
            if missing:
                problems.append(
                    f"Node '{node.name}' is missing {len(missing)} CPT row(s): {missing}"
                )
        return problems
 
    def is_valid(self):
        return len(self.validate()) == 0
 
    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes.values()],
        }
 
    @staticmethod
    def from_dict(data):
        bn = BayesianNetwork(name=data.get("name", "Untitled Network"))
        for node_data in data.get("nodes", []):
            node = Node.from_dict(node_data)
            bn.nodes[node.name] = node
        return bn
 
    def save(self, filepath):
        directory = os.path.dirname(filepath)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
 
    @staticmethod
    def load(filepath):
        if not os.path.isfile(filepath):
            raise NetworkError(f"File not found: {filepath}")
        with open(filepath, "r") as f:
            data = json.load(f)
        return BayesianNetwork.from_dict(data)
 
    def __repr__(self):
        return f"BayesianNetwork(name={self.name!r}, nodes={list(self.nodes.keys())})"
 