"""
controller/controller.py
 
BayesianNetworkController wires the Model (BayesianNetwork) and View
(CLIView) together. It owns the main loop, dispatches menu choices to
handler methods, and is the only layer that both calls model mutations
AND tells the view what to display. Neither Model nor View know about
each other.
"""

import os
 
from model.network import BayesianNetwork, NetworkError
from model.inference import query as run_inference, InferenceError
from view.graph_view import GraphView

GRAPHICS_DIR = "Graphics"
 
class BayesianNetworkController:
    def __init__(self, model=None, view=None, graph_view=None):
        self.network = model if model is not None else BayesianNetwork()
        self.view = view
        self.graph_view = graph_view if graph_view is not None else GraphView()
 
    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        dispatch = {
            "help": self.help,
            "rename network": self.rename_network,
            "add node": self.add_node,
            "remove node": self.remove_node,
            "rename node": self.rename_node,
            "add edge": self.add_edge,
            "remove edge": self.remove_edge,
            "define cpt": self.define_cpt,
            "show network": self.show_structure,
            "show node": self.show_node_details,
            "check network": self.validate_network,
            "query": self.run_query,
            "save": self.save_network,
            "load": self.load_network,
            "new": self.new_network,
            "export": self.export_graphic,
            "quit": None,
            "exit": None,
        }
        while True:
            choice = self.view.show_main_menu(self.network.name, len(self.network.nodes))
            if choice == "quit" or choice == "exit":
                self.view.show_goodbye()
                break
            handler = dispatch.get(choice)
            if handler is None:
                self.view.show_error("Not a valid option, try again.")
                continue
            try:
                handler()
            except (NetworkError, InferenceError) as e:
                self.view.show_error(str(e))
            except Exception as e:  # last-resort guard so the CLI never crashes outright
                self.view.show_error(f"Unexpected error: {e}")

    def help(self):
        self.view.help(self.network.name, len(self.network.nodes))
 
    # ------------------------------------------------------------------
    # Network Management
    # ------------------------------------------------------------------
    def rename_network(self):
        new_network_name = self.view.change_network_name()
        if not new_network_name:
            self.view.show_error("Network name cannot be empty.")
            return
        if new_network_name == self.network.name:
            self.view.show_error("New name cannot be the same as old name")
            return
        old_name = self.network.name
        self.network.set_name(new_network_name)
        self.view.show_success(f"Network renamed from '{old_name}' to '{new_network_name}'.")
 
    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------
    def add_node(self):
        name, states = self.view.get_new_node_info()
        if not name:
            self.view.show_error("Node name cannot be empty.")
            return
        if len(states) < 2:
            self.view.show_error("A node needs at least 2 states.")
            return
        self.network.add_node(name, states)
        self.view.show_success(f"Node '{name}' added with states {states}.")
 
    def remove_node(self):
        if not self.network.nodes:
            self.view.show_error("There are no nodes to remove.")
            return
        name = self.view.get_node_name_to_remove(self.network.node_names())
        if not name:
            return
        self.network.remove_node(name)
        self.view.show_success(f"Node '{name}' removed (and unlinked from any children).")
 
    def rename_node(self):
        if not self.network.nodes:
            self.view.show_error("There are no nodes to rename.")
            return
        name = self.view.get_node_to_rename(self.network.node_names())
        if not name:
            self.view.show_error("Node name cannot be empty.")
            return
        new_name = self.view.get_new_node_name()
        if not new_name:
            self.view.show_error("Node name cannot be empty.")
            return
        # Existence / uniqueness / validity are all checked inside
        # network.rename_node - the model is the single source of truth
        # for these rules, so we don't duplicate the checks here.
        self.network.rename_node(name, new_name)
        self.view.show_success(f"Node '{name}' renamed to '{new_name}'.")
 
    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------
    def add_edge(self):
        if len(self.network.nodes) < 2:
            self.view.show_error("You need at least 2 nodes to create a dependency.")
            return
        parent, child = self.view.get_edge_info(self.network.node_names())
        self.network.add_edge(parent, child)
        self.view.show_success(
            f"'{child}' now depends on '{parent}'. "
            f"Note: '{child}' CPT was reset - define it via option 5."
        )
 
    def remove_edge(self):
        if not self.network.nodes:
            self.view.show_error("There are no nodes yet.")
            return
        parent, child = self.view.get_edge_info(self.network.node_names(), action="remove")
        self.network.remove_edge(parent, child)
        self.view.show_success(f"Removed dependency: '{child}' no longer depends on '{parent}'.")
 
    # ------------------------------------------------------------------
    # CPT definition
    # ------------------------------------------------------------------
    def define_cpt(self):
        if not self.network.nodes:
            self.view.show_error("There are no nodes yet.")
            return
        node_name = self.view.get_node_name_for_cpt(self.network.node_names())
        node = self.network.get_node(node_name)  # raises NetworkError if missing
 
        combos = node.all_parent_combinations(self.network)
        self.view.announce_cpt_plan(node.name, node.states, node.parents, combos)
 
        for combo in combos:
            probs = self.view.get_cpt_row(node.name, node.states, node.parents, combo)
            try:
                self.network.set_cpt_row(node.name, combo, probs)
            except NetworkError as e:
                self.view.show_error(f"{e} -- please re-enter this row.")
                # retry this same row once more
                probs = self.view.get_cpt_row(node.name, node.states, node.parents, combo)
                self.network.set_cpt_row(node.name, combo, probs)
 
        self.view.show_success(f"CPT for '{node.name}' fully defined.")
 
    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    def show_structure(self):
        rows = []
        for name in self.network.node_names():
            node = self.network.get_node(name)
            rows.append(
                {
                    "name": node.name,
                    "states": node.states,
                    "parents": node.parents,
                    "fully_specified": node.is_fully_specified(self.network),
                }
            )
        self.view.show_network_structure(self.network.name, rows)
 
    def show_node_details(self):
        if not self.network.nodes:
            self.view.show_error("There are no nodes yet.")
            return
        node_name = self.view.get_node_name_for_display(self.network.node_names())
        node = self.network.get_node(node_name)
        children = self.network.children_of(node.name)
        cpt_rows = sorted(node.cpt.items())
        self.view.show_node_details(node.name, node.states, node.parents, children, cpt_rows)
 
    def validate_network(self):
        problems = self.network.validate()
        self.view.show_validation_result(problems)
 
    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def run_query(self):
        if not self.network.nodes:
            self.view.show_error("There are no nodes yet.")
            return
        query_var = self.view.get_query_variable(self.network.node_names())
        self.network.get_node(query_var)  # validates existence, raises otherwise
 
        other_nodes = {
            n: self.network.get_node(n).states
            for n in self.network.node_names()
            if n != query_var
        }
        evidence = self.view.get_evidence(other_nodes, query_var)
 
        distribution = run_inference(self.network, query_var, evidence)
        self.view.show_query_result(query_var, evidence, distribution)
 
    # ------------------------------------------------------------------
    # Save / load / new
    # ------------------------------------------------------------------
    def save_network(self):
        default_name = f"{self.network.name.replace(' ', '_')}.json"
        path = self.view.get_save_path(default_name)
        if not path:
            self.view.show_error("Save cancelled - no path given.")
            return
        self.network.save(path)
        self.view.show_success(f"Network saved to '{path}'.")
 
    def load_network(self):
        path = self.view.get_load_path()
        if not path:
            self.view.show_error("Load cancelled - no path given.")
            return
        loaded = BayesianNetwork.load(path)
        self.network = loaded
        self.view.show_success(
            f"Loaded network '{self.network.name}' with {len(self.network.nodes)} node(s)."
        )
 
    def new_network(self):
        if self.network.nodes:
            confirmed = self.view.confirm(
                "This will discard the current unsaved network. Continue?"
            )
            if not confirmed:
                self.view.show_message("Cancelled.")
                return
        name = self.view.get_new_network_name()
        self.network = BayesianNetwork(name=name)
        self.view.show_success(f"Started new network '{name}'.")

    # ------------------------------------------------------------------
    # Graphic export
    # ------------------------------------------------------------------
    def export_graphic(self):
        if not self.network.nodes:
            self.view.show_error("There are no nodes to draw.")
            return
 
        # topological_order() (not node_names()) is required here: a node
        # can be added before the node that later becomes its parent, so
        # insertion order alone doesn't guarantee parents precede children.
        # GraphView's level-assignment depends on that guarantee.
        order = self.network.topological_order()
        nodes_data = [
            {"name": name, "parents": self.network.get_node(name).parents}
            for name in order
        ]
        svg_content = self.graph_view.render_svg(nodes_data)
 
        default_filename = f"{self.network.name.replace(' ', '_')}.svg"
        filename = self.view.get_graphic_filename(default_filename)
        if not filename:
            self.view.show_error("Export cancelled - no filename given.")
            return
        if not filename.lower().endswith(".svg"):
            filename += ".svg"
 
        os.makedirs(GRAPHICS_DIR, exist_ok=True)
        filepath = os.path.join(GRAPHICS_DIR, filename)
        with open(filepath, "w") as f:
            f.write(svg_content)
 
        self.view.show_success(f"Network graphic saved to '{filepath}'.")
 