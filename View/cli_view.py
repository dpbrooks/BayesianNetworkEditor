"""
View/cli_view.py

CLIView owns every print() and input() call in the application. It knows
nothing about Node/BayesianNetwork internals beyond simple data it's handed
(names, lists, dicts) - all validation and logic live in the Controller/Model.
This keeps the View swappable (e.g. for a future GUI) without touching logic.
"""


class CLIView:
    # Single source of truth for every command's name(s), description, and
    # expected positional arguments - drives both the flat 'help' listing
    # and the detailed 'help <command>' lookup, so the two can never drift
    # out of sync with each other.
    COMMANDS = [  # noqa: RUF012
        {
            "keys": ["help"],
            "label": "Help",
            "description": "Displays commands and what they do.",
            "usage_args": ["Command Name"],
            "arg_help": [("Command Name", "optional - a specific command to show detailed help for")],
            "note": "With no argument, lists every command. With a command name, shows that command's detailed usage.",
        },
        {
            "keys": ["rename network"],
            "label": "Rename Network",
            "description": "Renames the network.",
            "usage_args": ["New Network Name"],
            "arg_help": [("New Network Name", "the network's new name")],
            "note": None,
        },
        {
            "keys": ["add node"],
            "label": "Add Node",
            "description": "Adds a new node to the network.",
            "usage_args": ["Node Name", "States"],
            "arg_help": [
                ("Node Name", "name for the new node"),
                ("States", "comma-separated list of possible states, e.g. True,False"),
            ],
            "note": None,
        },
        {
            "keys": ["remove node"],
            "label": "Remove Node",
            "description": "Removes a node from the network.",
            "usage_args": ["Node Name"],
            "arg_help": [("Node Name", "the node to remove")],
            "note": None,
        },
        {
            "keys": ["rename node"],
            "label": "Rename Node",
            "description": "Renames a node from the network.",
            "usage_args": ["Node Name", "New Node Name"],
            "arg_help": [
                ("Node Name", "the node to rename"),
                ("New Node Name", "its new name"),
            ],
            "note": None,
        },
        {
            "keys": ["add edge"],
            "label": "Add Edge",
            "description": "Designates a parent-child relationship between nodes.",
            "usage_args": ["Parent Node", "Child Node"],
            "arg_help": [
                ("Parent Node", "the cause"),
                ("Child Node", "the effect, depends on the parent"),
            ],
            "note": None,
        },
        {
            "keys": ["remove edge"],
            "label": "Remove Edge",
            "description": "Removes a parent-child relationship.",
            "usage_args": ["Parent Node", "Child Node"],
            "arg_help": [
                ("Parent Node", "the parent in the existing dependency"),
                ("Child Node", "the child in the existing dependency"),
            ],
            "note": None,
        },
        {
            "keys": ["define cpt"],
            "label": "Define CPT",
            "description": "Set probability of states for a node.",
            "usage_args": [],
            "arg_help": [],
            "note": (
                "Always fully interactive - any text typed after 'define cpt' is "
                "ignored. You'll be prompted for the node and then every "
                "probability row, one at a time."
            ),
        },
        {
            "keys": ["show network"],
            "label": "Show Network",
            "description": "Show the structure of the network.",
            "usage_args": [],
            "arg_help": [],
            "note": None,
        },
        {
            "keys": ["show node"],
            "label": "Show Node",
            "description": "Show details for one node.",
            "usage_args": ["Node Name"],
            "arg_help": [("Node Name", "the node to show details for")],
            "note": None,
        },
        {
            "keys": ["check network"],
            "label": "Check Network",
            "description": "Validate the network.",
            "usage_args": [],
            "arg_help": [],
            "note": None,
        },
        {
            "keys": ["query"],
            "label": "Query",
            "description": "Run an inference query.",
            "usage_args": ["Node Name"],
            "arg_help": [("Node Name", "the variable to compute a probability distribution for")],
            "note": (
                "After the query variable is set, you'll always be asked "
                "interactively for evidence (known values for the other "
                "variables) - that part can't be filled in on the same line."
            ),
        },
        {
            "keys": ["save"],
            "label": "Save",
            "description": "Save network as a json file.",
            "usage_args": ["File Path"],
            "arg_help": [("File Path", "where to save the network (defaults to the network's name)")],
            "note": None,
        },
        {
            "keys": ["load"],
            "label": "Load",
            "description": "Loads a network from a json file.",
            "usage_args": ["File Path"],
            "arg_help": [("File Path", "the file to load")],
            "note": None,
        },
        {
            "keys": ["new"],
            "label": "New",
            "description": "Starts a new network.",
            "usage_args": ["Network Name"],
            "arg_help": [("Network Name", "name for the new network (defaults to 'Untitled Network')")],
            "note": None,
        },
        {
            "keys": ["export"],
            "label": "Export",
            "description": "Exports network as a graphic (SVG).",
            "usage_args": ["Filename"],
            "arg_help": [("Filename", "saved under ./Graphics/ (defaults to the network's name)")],
            "note": None,
        },
        {
            "keys": ["quit", "exit"],
            "label": "Quit/Exit",
            "description": "Exits the program.",
            "usage_args": [],
            "arg_help": [],
            "note": None,
        },
    ]

    # Derived from COMMANDS (rather than kept as a separate literal) so the
    # parser and the help text can never disagree about which commands are
    # two words. Checked before falling back to a single-word match, so
    # e.g. 'add node Rain Yes,No' resolves to the command 'add node' (not
    # the nonexistent single-word command 'add').
    MULTI_WORD_COMMANDS = {key for entry in COMMANDS for key in entry["keys"] if " " in key}  # noqa: RUF012

    # Every alias (e.g. both 'quit' and 'exit') maps to its shared entry.
    _COMMAND_LOOKUP = {key: entry for entry in COMMANDS for key in entry["keys"]}  # noqa: RUF012

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

    def help(self, network_name, node_count, remainder=""):
        self.show_header(f"Bayesian Network: {network_name}  ({node_count} node(s))")
        sub_command, _ = self._parse_command(remainder)
        if not sub_command:
            for entry in self.COMMANDS:
                print(f"  {entry['label']:<15}-> {entry['description']}")
            return
        entry = self._COMMAND_LOOKUP.get(sub_command)
        if entry is None:
            self.show_error(f"Unknown command '{remainder.strip()}'. Type 'help' to see all commands.")
            return
        self._show_command_help(entry)

    def _show_command_help(self, entry):
        print(f"{entry['label']}: {entry['description']}")
        primary_key = entry["keys"][0]
        if entry["usage_args"]:
            usage_str = " ".join(f"[{a}]" for a in entry["usage_args"])
            print(f"\nUsage: {primary_key} {usage_str}")
            for arg_name, explanation in entry["arg_help"]:
                print(f"  {arg_name:<16}: {explanation}")
            print(
                "\nEach argument is optional - any left out will be prompted for, "
                "one at a time, in the order shown. You can't skip ahead (e.g. "
                "providing a later argument without the ones before it)."
            )
        else:
            print(f"\nUsage: {primary_key}")
            print("This command takes no arguments.")
        if entry["note"]:
            print(f"\nNote: {entry['note']}")


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
            bar = "#" * round(prob * 40)
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