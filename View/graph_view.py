"""
View/graph_view.py
 
GraphView renders a Bayesian Network's structure (nodes + edges) as a
standalone SVG image: a layered, top-down directed graph with parents
drawn above their children and arrows showing each dependency. Nodes
belonging to entirely separate (disconnected) subgraphs are grouped
together within each shared depth level, rather than left interleaved.
 
Like CLIView, this class only deals in plain data handed to it - a list
of {"name": str, "parents": list[str]} dicts - and knows nothing about
the Node/BayesianNetwork classes. It builds SVG markup with plain string
formatting (pure standard library, no matplotlib/graphviz/networkx), so
the generated .svg file opens in any browser or image viewer without
installing anything extra.
"""
 
 
class GraphView:
    NODE_HEIGHT = 50
    NODE_H_GAP = 40         # horizontal gap between boxes on the same level
    NODE_V_GAP = 90         # vertical gap between levels
    MARGIN = 50
    CHAR_WIDTH = 8           # rough average glyph width at the font size used below
    MIN_NODE_WIDTH = 90
    FONT_SIZE = 14
    MIN_LEVEL_STAGGER = 60   # smallest allowed offset between alternating levels
    STAGGER_CLEARANCE = 30   # target gap between a skip-level line and a box edge
    COMPONENT_GAP = 100      # extra horizontal space between separate connected
                             # components that happen to share a depth level
    REFINEMENT_PASSES = 6    # alternating bottom-up/top-down coordinate passes
                             # after the initial layout, to let a root settle
                             # into place over the true center of its subtree
 
    def render_svg(self, nodes):
        """
        nodes: list of dicts {"name": str, "parents": list[str]}, given in
               an order where every parent appears before any of its
               children (i.e. a topological order). Producing that order
               is the Controller's job (via network.topological_order());
               this class only lays out and draws whatever it's given.
 
        Returns the full SVG document as a string.
        """
        if not nodes:
            return self._empty_svg()
 
        levels = self._assign_levels(nodes)
        component_id, component_rank, order_index = self._compute_components(nodes)
        stagger = self._stagger_amount(nodes)
        positions = self._compute_positions(
            nodes, levels, stagger, component_id, component_rank, order_index
        )
        width, height = self._canvas_size(positions)
 
        parts = [self._svg_header(width, height), self._arrow_marker()]
        # Edges first so node boxes are drawn on top of the lines feeding into them.
        for node in nodes:
            for parent in node["parents"]:
                parts.append(self._edge_svg(positions[parent], positions[node["name"]]))
        for node in nodes:
            parts.append(self._node_svg(node["name"], positions[node["name"]]))
        parts.append("</svg>")
        return "\n".join(parts)
 
    # ------------------------------------------------------------------
    # Connected components
    # ------------------------------------------------------------------
    def _compute_components(self, nodes):
        """
        Union-Find over the undirected version of the graph (an edge
        connects a parent and child regardless of direction), so entirely
        separate subgraphs can be recognized as such. Without this, two
        unrelated components can end up with their nodes interleaved on
        the same level just because they happen to land at the same
        depth from their own (unrelated) roots - which reads as one
        tangled graph instead of clearly separate pieces.
 
        Returns:
            component_id:   {node_name: component root label}
            component_rank: {component root label: index of the earliest
                              node (in `nodes` order) belonging to it} -
                              used to order components left-to-right in a
                              way that matches how the network was built,
                              rather than an arbitrary union-find label.
            order_index:    {node_name: its index in `nodes`} - used as
                              the tie-breaker within a component.
        """
        order_index = {n["name"]: i for i, n in enumerate(nodes)}
        uf_parent = {n["name"]: n["name"] for n in nodes}
 
        def find(x):
            while uf_parent[x] != x:
                uf_parent[x] = uf_parent[uf_parent[x]]
                x = uf_parent[x]
            return x
 
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                uf_parent[ra] = rb
 
        for node in nodes:
            for p in node["parents"]:
                if p in uf_parent:  # ignore a dangling parent reference defensively
                    union(p, node["name"])
 
        component_id = {name: find(name) for name in uf_parent}
 
        component_rank = {}
        for node in nodes:
            cid = component_id[node["name"]]
            if cid not in component_rank:
                component_rank[cid] = order_index[node["name"]]
 
        return component_id, component_rank, order_index
 
    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _assign_levels(self, nodes):
        """
        level(node) = 0 for a root, else 1 + max(level(parent) for parent
        in node['parents']). Requires `nodes` to already be in topological
        order so every parent's level is known before it's needed.
        """
        levels = {}
        for node in nodes:
            if not node["parents"]:
                levels[node["name"]] = 0
            else:
                levels[node["name"]] = 1 + max(levels[p] for p in node["parents"])
        return levels
 
    def _compute_positions(self, nodes, levels, stagger, component_id, component_rank, order_index):
        """
        Two ideas make this more balanced than pure left-to-right packing:
 
        1. Barycenter placement: a node's desired x is the average x of its
           own parents (or, in the refinement passes below, its own
           children). A node with two parents far apart settles between
           them instead of directly under either one.
        2. Iterative refinement (see the loop below) + row centering (see
           `_center_rows`): a single top-down pass only pulls each node
           toward its parents, so a root sitting above a wide fan-out of
           descendants has no way to "know" how wide its own subtree ends
           up - it just stays wherever the initial packing left it, which
           drifts further off-center the further a component sits from
           the middle of the diagram. Alternating bottom-up (children)
           and top-down (parents) passes lets that influence propagate
           both ways until positions settle - a root ends up centered
           over its actual descendants, not just its immediate children.
 
        Overlaps are still impossible: the left-to-right ORDER within each
        level is decided once, in the first pass (grouped by component,
        then by barycenter), and frozen from then on - refinement passes
        only nudge coordinates via the same left-to-right compaction
        (never left of the previous box), so component grouping and the
        no-overlap guarantee both survive every later pass.
        """
        node_lookup = {n["name"]: n for n in nodes}
        children_map = {n["name"]: [] for n in nodes}
        for n in nodes:
            for p in n["parents"]:
                children_map[p].append(n["name"])
 
        level_rows = {}
        for node in nodes:
            level_rows.setdefault(levels[node["name"]], []).append(node["name"])
        level_numbers = sorted(level_rows.keys())
 
        # --- Pass 1 (top-down): establishes the initial layout AND the
        # left-to-right order for each level (component, then barycenter
        # of parents) - this order is frozen for every pass after this one.
        positions = {}
        ordered_rows = {}
        for level in level_numbers:
            names = level_rows[level]
            if level == 0:
                desired = {n: None for n in names}
            else:
                desired = {
                    n: sum(positions[p]["x"] for p in node_lookup[n]["parents"]) / len(node_lookup[n]["parents"])
                    for n in names
                }
            ordered = sorted(
                names,
                key=lambda n: (
                    component_rank[component_id[n]],
                    desired[n] if desired[n] is not None else 0.0,
                    order_index[n],
                ),
            )
            ordered_rows[level] = ordered
            self._place_row(positions, ordered, level, stagger, component_id, desired)
 
        # --- Passes 2+: alternate bottom-up (barycenter of children) and
        # top-down (barycenter of parents) coordinate refinement, reusing
        # the frozen order from pass 1 each time.
        for i in range(self.REFINEMENT_PASSES):
            going_up = i % 2 == 0
            sweep = reversed(level_numbers) if going_up else level_numbers
            for level in sweep:
                names = ordered_rows[level]
                if going_up:
                    refs = {n: [positions[c]["x"] for c in children_map[n]] for n in names}
                else:
                    refs = {n: [positions[p]["x"] for p in node_lookup[n]["parents"]] for n in names}
                desired = {n: (sum(refs[n]) / len(refs[n]) if refs[n] else positions[n]["x"]) for n in names}
                self._place_row(positions, names, level, stagger, component_id, desired)
 
        self._center_rows(positions, level_rows, component_id)
        self._reflow_components(positions, level_rows, component_id, component_rank)
        self._normalize_to_margin(positions)
        return positions
 
    def _normalize_to_margin(self, positions):
        """
        Shift the entire diagram (every node, by the same amount) so the
        true leftmost edge lands exactly at MARGIN. Nothing earlier in the
        pipeline guarantees that: `_center_rows` and `_reflow_components`
        both only ever move things *relative* to each other (a component's
        own rows relative to its own bounding box, then whole components
        relative to their neighbors) - there's no step that pins the
        overall leftmost point back to the margin. Left unchecked, that
        leftover offset doesn't grow in absolute pixels, but as merges
        shrink the total diagram width (fewer separate component blocks),
        the same fixed offset eats a bigger and bigger fraction of the
        image, reading as ever-increasing left-side whitespace.
        """
        if not positions:
            return
        min_left = min(p["x"] - p["w"] / 2 for p in positions.values())
        shift = self.MARGIN - min_left
        if shift:
            for p in positions.values():
                p["x"] += shift
 
    def _reflow_components(self, positions, level_rows, component_id, component_rank):
        """
        `_center_rows` balances each component's own rows against its own
        bounding box - necessary so a root stays centered over its own
        subtree - but that shifts each component independently, with no
        awareness of where a neighboring component's edge ended up. Two
        components can end up drifting much closer together or further
        apart than COMPONENT_GAP as a result. This pass corrects that:
        each component is treated as one rigid block (its internal layout,
        already balanced, is left completely untouched) and the blocks are
        placed left-to-right, in the same order used everywhere else, so
        that every pair of neighboring components ends up exactly
        COMPONENT_GAP apart - no more, no less.
        """
        if not positions:
            return
 
        members_by_component = {}
        for names in level_rows.values():
            for name in names:
                members_by_component.setdefault(component_id[name], []).append(name)
 
        components = []
        for cid, members in members_by_component.items():
            left = min(positions[n]["x"] - positions[n]["w"] / 2 for n in members)
            right = max(positions[n]["x"] + positions[n]["w"] / 2 for n in members)
            components.append((component_rank[cid], left, right, members))
        components.sort(key=lambda c: c[0])
 
        cursor = None
        for _, left, right, members in components:
            target_left = left if cursor is None else cursor
            shift = target_left - left
            if shift:
                for n in members:
                    positions[n]["x"] += shift
            cursor = target_left + (right - left) + self.COMPONENT_GAP
 
    def _place_row(self, positions, ordered_names, level, stagger, component_id, desired):
        """
        Lay out one level's row left-to-right in the given order, pulling
        each node toward its `desired` x (its parents' or children's
        barycenter, or None to just pack it at the next open slot) but
        never left of the previous box - this is what keeps overlaps
        structurally impossible no matter how the desired positions shift
        between refinement passes.
        """
        y = self.MARGIN + level * (self.NODE_HEIGHT + self.NODE_V_GAP) + self.NODE_HEIGHT / 2
        next_left = self.MARGIN + self._level_stagger(level, stagger)
        prev_right = None
        prev_component = None
        for name in ordered_names:
            w = self._node_width(name)
            cid = component_id[name]
            gap = self.COMPONENT_GAP if (prev_component is not None and cid != prev_component) else self.NODE_H_GAP
            min_left = next_left if prev_right is None else (prev_right + gap)
            d = desired.get(name)
            left = min_left if d is None else max(d - w / 2, min_left)
            positions[name] = {"x": left + w / 2, "y": y, "w": w}
            prev_right = left + w
            prev_component = cid
 
    def _center_rows(self, positions, level_rows, component_id):
        """
        Center each row within its OWN component's bounding box - not the
        whole diagram's. A row is centered against every other row that
        belongs to the same component, regardless of what other unrelated
        components are doing elsewhere in the diagram.
 
        This matters whenever one component's rows don't line up with
        another's, most obviously when a component reaches a depth no
        other component does: e.g. after adding an edge that pushes one
        subtree a level deeper than everything else, a node left alone at
        that new deepest level would - if centered against the *whole*
        diagram - snap toward the horizontal middle of the entire graph,
        which likely belongs to a totally unrelated component. Centering
        per-component keeps it anchored over its own subtree instead.
        """
        if not positions:
            return
 
        rows_by_component = {}
        for level, names in level_rows.items():
            for name in names:
                cid = component_id[name]
                rows_by_component.setdefault(cid, {}).setdefault(level, []).append(name)
 
        for rows in rows_by_component.values():
            all_names = [n for names in rows.values() for n in names]
            comp_left = min(positions[n]["x"] - positions[n]["w"] / 2 for n in all_names)
            comp_right = max(positions[n]["x"] + positions[n]["w"] / 2 for n in all_names)
            comp_width = comp_right - comp_left
 
            for names in rows.values():
                row_left = min(positions[n]["x"] - positions[n]["w"] / 2 for n in names)
                row_right = max(positions[n]["x"] + positions[n]["w"] / 2 for n in names)
                row_width = row_right - row_left
                offset = (comp_width - row_width) / 2 - (row_left - comp_left)
                if offset:
                    for n in names:
                        positions[n]["x"] += offset
 
    def _level_stagger(self, level, stagger):
        """
        Extra horizontal offset for this level, alternating between two
        alignments (0 and `stagger`) as depth increases. Without this,
        every level starts flush against the same left margin, so a
        skip-level edge (e.g. a grandparent linking directly to a
        grandchild) can land almost exactly on top of the node in
        between them - the line reads as passing straight through that
        node instead of around it. Alternating the starting offset means
        adjacent levels are horizontally offset from each other, so an
        intermediate node no longer sits on the straight line between a
        node two levels above it and its shared descendant.
        """
        return stagger if level % 2 == 1 else 0
 
    def _stagger_amount(self, nodes):
        """
        Size the stagger to the actual content instead of using a fixed
        pixel value: wider boxes (longer node names) need a bigger offset
        to keep the same visual clearance between a skip-level line and
        an intermediate node's edge. Based on the widest box anywhere in
        the diagram, since two nodes on the same "phase" (both odd or
        both even levels) can be up to that wide.
        """
        widest = max((self._node_width(n["name"]) for n in nodes), default=self.MIN_NODE_WIDTH)
        return max(self.MIN_LEVEL_STAGGER, widest / 2 + self.STAGGER_CLEARANCE)
 
    def _node_width(self, name):
        return max(self.MIN_NODE_WIDTH, len(name) * self.CHAR_WIDTH + 30)
 
    def _canvas_size(self, positions):
        """Derived directly from the final positions so it can never drift
        out of sync with however they were laid out (stagger, component
        gaps, etc. all already baked into `positions`)."""
        max_right = max(p["x"] + p["w"] / 2 for p in positions.values())
        max_bottom = max(p["y"] for p in positions.values()) + self.NODE_HEIGHT / 2
        width = int(max_right + self.MARGIN)
        height = int(max_bottom + self.MARGIN)
        return width, height
 
    # ------------------------------------------------------------------
    # SVG fragments
    # ------------------------------------------------------------------
    def _svg_header(self, width, height):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" '
            f'font-family="Helvetica, Arial, sans-serif">'
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="white"/>'
        )
 
    def _arrow_marker(self):
        return (
            '<defs><marker id="arrowhead" markerWidth="10" markerHeight="7" '
            'refX="9" refY="3.5" orient="auto">'
            '<polygon points="0 0, 10 3.5, 0 7" fill="#333333"/>'
            '</marker></defs>'
        )
 
    def _edge_svg(self, parent_pos, child_pos):
        x1, y1 = parent_pos["x"], parent_pos["y"] + self.NODE_HEIGHT / 2
        x2, y2 = child_pos["x"], child_pos["y"] - self.NODE_HEIGHT / 2
        return (
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#333333" stroke-width="1.5" marker-end="url(#arrowhead)"/>'
        )
 
    def _node_svg(self, name, pos):
        x, y, w = pos["x"], pos["y"], pos["w"]
        left, top = x - w / 2, y - self.NODE_HEIGHT / 2
        safe_name = self._escape(name)
        return (
            f'<rect x="{left:.1f}" y="{top:.1f}" width="{w:.1f}" '
            f'height="{self.NODE_HEIGHT}" rx="10" ry="10" '
            f'fill="#eaf2ff" stroke="#2c5aa0" stroke-width="1.5"/>'
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="{self.FONT_SIZE}" '
            f'fill="#1a1a1a">{safe_name}</text>'
        )
 
    def _escape(self, text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
 
    def _empty_svg(self):
        w, h = 400, 120
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'font-family="Helvetica, Arial, sans-serif">'
            f'<rect width="{w}" height="{h}" fill="white"/>'
            f'<text x="{w / 2}" y="{h / 2}" text-anchor="middle" font-size="16" '
            f'fill="#888888">(empty network - no nodes to draw)</text>'
            f'</svg>'
        )
 
