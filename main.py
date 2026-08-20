#!/usr/bin/env python3
"""
main.py

Entry point. Wires together the Model (BayesianNetwork), View (CLIView),
and Controller (BayesianNetworkController) and starts the CLI loop.

Usage:
    python3 main.py
"""

from model.network import BayesianNetwork
from view.cli_view import CLIView
from controller.controller import BayesianNetworkController


def main():
    model = BayesianNetwork(name="Untitled Network")
    view = CLIView()
    controller = BayesianNetworkController(model=model, view=view)

    view.show_message("Welcome to the Bayesian Network Builder.")
    view.show_message(
        "Build a network from scratch (options 1-5), or load an example / saved "
        "file (option 11) to explore inference (option 9) right away.\n"
        "Tip: try loading 'examples/alarm_network.json' to see a worked example."
    )
    controller.run()


if __name__ == "__main__":
    main()
