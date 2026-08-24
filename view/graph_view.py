"""
view/graph_view.py

GraphView renders a Bayesian Network's structure (nodes + edges) as a
standalone SVG image: a layered, top-down directed graph with parents
drawn above their children and arrows showing each dependency.

Like CLIView, this class only deals in plain data handed to it - a list
of {"name": str, "parents": list[str]} dicts - and knows nothing about
the Node/BayesianNetwork classes. It builds SVG markup with plain string
formatting (pure standard library, no matplotlib/graphviz/networkx), so
the generated .svg file opens in any browser or image viewer without
installing anything extra.
"""


class GraphView:
    NODE_HEIGHT = 50
    NODE_H_GAP = 40      # horizontal gap between boxes on the same level
    NODE_V_GAP = 90       # vertical gap between levels
    MARGIN = 50
    CHAR_WIDTH = 8         # rough average glyph width at the font size used below
    MIN_NODE_WIDTH = 90
    FONT_SIZE = 14
    MIN_LEVEL_STAGGER = 60  # smallest allowed offset between alternating levels
    STAGGER_CLEARANCE = 30  # target gap between a skip-level line and a box edge

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
        stagger = self._stagger_amount(nodes)
        positions, level_rows = self._compute_positions(nodes, levels, stagger)
        width, height = self._canvas_size(level_rows, stagger)

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

    def _compute_positions(self, nodes, levels, stagger):
        level_rows = {}
        for node in nodes:
            level_rows.setdefault(levels[node["name"]], []).append(node["name"])

        positions = {}
        for level, names in level_rows.items():
            y = self.MARGIN + level * (self.NODE_HEIGHT + self.NODE_V_GAP) + self.NODE_HEIGHT / 2
            x = self.MARGIN + self._level_stagger(level, stagger)
            for name in names:
                w = self._node_width(name)
                positions[name] = {"x": x + w / 2, "y": y, "w": w}
                x += w + self.NODE_H_GAP
        return positions, level_rows

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

    def _canvas_size(self, level_rows, stagger):
        max_row_width = 0
        for level, names in level_rows.items():
            row_width = (
                self._level_stagger(level, stagger)
                + sum(self._node_width(n) for n in names)
                + self.NODE_H_GAP * (len(names) - 1)
            )
            max_row_width = max(max_row_width, row_width)
        width = max_row_width + 2 * self.MARGIN
        num_levels = max(level_rows.keys()) + 1 if level_rows else 1
        height = num_levels * (self.NODE_HEIGHT + self.NODE_V_GAP) + 2 * self.MARGIN
        return int(width), int(height)

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
