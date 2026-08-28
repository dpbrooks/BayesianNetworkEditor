"""
View/cli_view.py
 
CLIView owns every print() and input() call in the application. It knows
nothing about Node/BayesianNetwork internals beyond simple data it's handed
(names, lists, dicts) - all validation and logic live in the Controller/Model.
This keeps the View swappable (e.g. for a future GUI) without touching logic.
"""
 
 
class CLIView:
    # Recognized two-word commands. Checked before falling back to a
    # single-word match, so e.g. 'add node Rain Yes,No' resolves to the
    # command 'add node' (not the nonexistent single-word command 'add').
    # None of these words overlap with a single-word command's own name,
    # so there's never any ambiguity about which one matched.
    MULTI_WORD_COMMANDS = {
        "rename network", "add node", "remove node", "rename node",
        "add edge", "remove edge", "define cpt", "show network",
        "show node", "check network",
    }
 
    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    def show_message(self, message):
        print(message)
 
    def show_error(self, message):
        print(f"  !! Error: {message}")
 
    def show_success(self, message):
        print(f"  -> {message}")
 
    def show_header(self, title):
        print("\n" + "=" * 60)
        print(title)
        print("=" * 60)
 
    def prompt(self, text):
        return input(f"{text}: ").strip()
 
    def confirm(self, text):
        answer = input(f"{text} [y/N]: ").strip().lower()
        return answer in ("y", "yes")
 
    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------
    def show_main_menu(self, network_name, node_count):
        """
        Returns (command, remainder). `remainder` is whatever text (if
        any) followed the command on the same line, with its original
        spacing and case intact - callers split it further per-field as
        needed, so e.g. a file path or node name keeps its exact casing
        even though the command itself is matched case-insensitively.
        """
        self.show_header(f"Bayesian Network: {network_name}  ({node_count} node(s))")
        raw = input("\nEnter Command ('help' for list of commands): ").strip()
        return self._parse_command(raw)
 
    def _parse_command(self, raw):
        raw = raw.strip()
        if not raw:
            return "", ""
        # split(None, 2) yields at most 3 pieces, with the 3rd (if any)
        # holding everything after the first two words untouched - that's
        # what lets us test a 2-word command without mangling the rest.
        three_parts = raw.split(None, 2)
        two_word_candidate = (
            f"{three_parts[0]} {three_parts[1]}".lower() if len(three_parts) >= 2 else None
        )
        if two_word_candidate in self.MULTI_WORD_COMMANDS:
            remainder = three_parts[2] if len(three_parts) == 3 else ""
            return two_word_candidate, remainder
        two_parts = raw.split(None, 1)
        command = two_parts[0].lower()
        remainder = two_parts[1] if len(two_parts) == 2 else ""
        return command, remainder
 
    def help(self, network_name, node_count):
        self.show_header(f"Bayesian Network: {network_name}  ({node_count} node(s))")
        commands = [
            ("Help", "Displays commands and what they do"),
            ("Rename Network", "Renames the network"),
            ("Add Node", "Adds a new node to the network"),
            ("Remove Node", "Removes a node from the network"),
            ("Rename Node", "Renames a node from the network"),
            ("Add Edge", "Designates a parent-child relationship between nodes"),
            ("Remove Edge", "Removes a parent-child relationship"),
            ("Define CPT", "Set probability of states for a node"),
            ("Show Network", "Show the structure of the network"),
            ("Show Node", "Show details for one node"),
            ("Check Network", "Validate the network"),
            ("Query", "Run an inference query"),
            ("Save", "Save network as a json file"),
            ("Load", "Loads a network from a json file"),
            ("New", "Starts a new network"),
            ("Export", "Exports network as a graphic (SVG)"),
            ("Quit/Exit", "Exits the program")
        ]
        for key, label in commands:
            print(f"  {key:<15}-> {label}")
 
 
    # ------------------------------------------------------------------
    # Network Management
    # ------------------------------------------------------------------
    def change_network_name(self, prefilled=None):
        if prefilled:
            return prefilled
        return self.prompt("New network name")
 
    # ------------------------------------------------------------------
    # Node creation / removal
    # ------------------------------------------------------------------
    def get_new_node_info(self, prefilled_name=None, prefilled_states=None):
        name = prefilled_name if prefilled_name else self.prompt("New node name")
        if prefilled_states:
            states_raw = prefilled_states
        else:
            states_raw = self.prompt(
                "States for this node, comma-separated (e.g. True,False)"
            )
        states = [s.strip() for s in states_raw.split(",") if s.strip()]
        return name, states
 
    def get_node_name_to_remove(self, node_names, prefilled=None):
        if prefilled:
            return prefilled
        self._list_nodes_inline(node_names)
        return self.prompt("Name of node to remove")
 
    def get_node_to_rename(self, node_names, prefilled=None):
        if prefilled:
            return prefilled
        self._list_nodes_inline(node_names)
        return self.prompt("Name of node to rename")
 
    def get_new_node_name(self, prefilled=None):
        if prefilled:
            return prefilled
        return self.prompt("Enter new name for node")
 
    def _list_nodes_inline(self, node_names):
        if not node_names:
            self.show_message("  (no nodes defined yet)")
        else:
            self.show_message("  Existing nodes: " + ", ".join(node_names))
 
    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------
    def get_edge_info(self, node_names, prefilled_parent=None, prefilled_child=None, action="add"):
        if prefilled_parent is None or prefilled_child is None:
            self._list_nodes_inline(node_names)
        if action == "remove":
            parent = prefilled_parent or self.prompt("Parent node (in the existing dependency to remove)")
            child = prefilled_child or self.prompt("Child node (in the existing dependency to remove)")
        else:
            parent = prefilled_parent or self.prompt("Parent node (the cause)")
            child = prefilled_child or self.prompt("Child node (the effect, depends on the parent)")
        return parent, child
 
    # ------------------------------------------------------------------
    # CPT entry
    # ------------------------------------------------------------------
    def get_node_name_for_cpt(self, node_names):
        self._list_nodes_inline(node_names)
        return self.prompt("Which node's probability table do you want to define")
 
    def announce_cpt_plan(self, node_name, states, parents, combinations):
        self.show_header(f"Defining CPT for '{node_name}'")
        self.show_message(f"States: {states}")
        if parents:
            self.show_message(f"Parents: {parents}")
            self.show_message(
                f"You will enter {len(combinations)} row(s), one per parent-state combination."
            )
        else:
            self.show_message("This node has no parents - you will enter 1 row (the prior).")
 
    def get_cpt_row(self, node_name, states, parents, parent_combo):
        if parent_combo:
            desc = ", ".join(f"{p}={v}" for p, v in zip(parents, parent_combo))
            self.show_message(f"\n  Given: {desc}")
        else:
            self.show_message("\n  (no conditions - prior probability)")
 
        probs = []
        for state in states:
            while True:
                raw = self.prompt(f"    P({node_name} = {state})")
                try:
                    p = float(raw)
                except ValueError:
                    self.show_error("Please enter a number (e.g. 0.3).")
                    continue
                if p < 0 or p > 1:
                    self.show_error("Probability must be between 0 and 1.")
                    continue
                probs.append(p)
                break
        return probs
 
    # ------------------------------------------------------------------
    # Display: structure, node detail, validation
    # ------------------------------------------------------------------
    def get_node_name_for_display(self, node_names, prefilled=None):
        if prefilled:
            return prefilled
        self._list_nodes_inline(node_names)
        return self.prompt("Which node do you want to select")
    
    def show_network_structure(self, name, rows):
        """
        rows: list of dicts {name, states, parents, fully_specified}
        """
        self.show_header(f"Network structure: {name}")
        if not rows:
            self.show_message("  (empty network - add some nodes!)")
            return
        for r in rows:
            status = "OK" if r["fully_specified"] else "INCOMPLETE (missing CPT rows)"
            parents_str = ", ".join(r["parents"]) if r["parents"] else "(none - root node)"
            print(f"  * {r['name']}")
            print(f"      states : {r['states']}")
            print(f"      parents: {parents_str}")
            print(f"      status : {status}")
 
    def show_node_details(self, node_name, states, parents, children, cpt_rows):
        """
        cpt_rows: list of (parent_value_tuple, probability_list) already defined
        """
        self.show_header(f"Node: {node_name}")
        self.show_message(f"States  : {states}")
        self.show_message(f"Parents : {parents if parents else '(none)'}")
        self.show_message(f"Children: {children if children else '(none)'}")
        self.show_message("CPT:")
        if not cpt_rows:
            self.show_message("  (no rows defined yet)")
        else:
            for parent_vals, probs in cpt_rows:
                cond = (
                    ", ".join(f"{p}={v}" for p, v in zip(parents, parent_vals))
                    if parent_vals
                    else "prior"
                )
                probs_str = ", ".join(
                    f"{s}={p:.4f}" for s, p in zip(states, probs)
                )
                print(f"    [{cond}]  ->  {probs_str}")
 
    def show_validation_result(self, problems):
        if not problems:
            self.show_success("Network is valid and fully specified - ready for inference.")
        else:
            self.show_error(f"Found {len(problems)} problem(s):")
            for p in problems:
                print(f"    - {p}")
 
    # ------------------------------------------------------------------
    # Inference query
    # ------------------------------------------------------------------
    def get_query_variable(self, node_names, prefilled=None):
        if prefilled:
            return prefilled
        self._list_nodes_inline(node_names)
        return self.prompt("Node to query (the variable you want a probability for)")
 
    def get_evidence(self, network_node_info, query_var):
        """
        network_node_info: dict {name: states}, excludes query_var already
        Returns dict {name: state}
        """
        evidence = {}
        self.show_message(
            "\nEnter evidence (known values). Leave blank to skip a variable."
        )
        for name, states in network_node_info.items():
            if name == query_var:
                continue
            raw = self.prompt(f"  {name} (states: {states}, blank = unknown)")
            if raw:
                evidence[name] = raw
        return evidence
 
    def show_query_result(self, query_var, evidence, distribution):
        self.show_header(f"P({query_var} | evidence)")
        if evidence:
            self.show_message("Evidence: " + ", ".join(f"{k}={v}" for k, v in evidence.items()))
        else:
            self.show_message("Evidence: (none)")
        for state, prob in distribution.items():
            bar = "#" * int(round(prob * 40))
            print(f"  {state:>15} : {prob:.4f}  {bar}")
 
    # ------------------------------------------------------------------
    # Save / load
    # ------------------------------------------------------------------
    def get_save_path(self, default_name, prefilled=None):
        if prefilled:
            return prefilled
        raw = self.prompt(f"File path to save to [default: {default_name}]")
        return raw if raw else default_name
 
    def get_load_path(self, prefilled=None):
        if prefilled:
            return prefilled
        return self.prompt("File path to load")
 
    def get_new_network_name(self, prefilled=None):
        if prefilled:
            return prefilled
        raw = self.prompt("Name for the new network [default: Untitled Network]")
        return raw if raw else "Untitled Network"
 
    # ------------------------------------------------------------------
    # Graphic export
    # ------------------------------------------------------------------
    def get_graphic_filename(self, default_name, prefilled=None):
        if prefilled:
            return prefilled
        raw = self.prompt(
            f"Filename for the graphic, saved under ./Graphics/ [default: {default_name}]"
        )
        return raw if raw else default_name
    
    def show_goodbye(self):
        self.show_message("\nGoodbye!")
 