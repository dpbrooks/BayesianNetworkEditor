"""
model/inference.py

Exact probabilistic inference over a BayesianNetwork using the
"enumeration-ask" algorithm (Russell & Norvig, AIMA). Suitable for the
small/medium hand-built networks this CLI is meant for.

Public entry point:
    query(network, query_var, evidence) -> dict {state: probability}
"""

from model.network import NetworkError


class InferenceError(Exception):
    pass


def query(network, query_var, evidence=None):
    """
    Compute P(query_var | evidence) as a normalized distribution over
    query_var's states.

    evidence: dict of {variable_name: state_value}, may be empty/None.
    """
    evidence = dict(evidence) if evidence else {}

    if query_var not in network.nodes:
        raise InferenceError(f"No node named '{query_var}'.")
    for var, val in evidence.items():
        if var not in network.nodes:
            raise InferenceError(f"Evidence variable '{var}' does not exist.")
        if val not in network.get_node(var).states:
            raise InferenceError(f"'{val}' is not a valid state of '{var}'.")
    if query_var in evidence:
        raise InferenceError(f"Query variable '{query_var}' cannot also be evidence.")

    problems = network.validate()
    if problems:
        raise InferenceError(
            "Network is not ready for inference:\n  - " + "\n  - ".join(problems)
        )

    var_order = network.topological_order()

    distribution = {}
    query_node = network.get_node(query_var)
    for state in query_node.states:
        extended_evidence = dict(evidence)
        extended_evidence[query_var] = state
        distribution[state] = _enumerate_all(network, list(var_order), extended_evidence)

    total = sum(distribution.values())
    if total <= 0:
        raise InferenceError(
            "The evidence provided has zero probability under this network "
            "(cannot normalize)."
        )
    return {state: prob / total for state, prob in distribution.items()}


def _enumerate_all(network, variables, evidence):
    """Recursively sum out non-evidence variables, in topological order."""
    if not variables:
        return 1.0

    Y = variables[0]
    rest = variables[1:]
    node = network.get_node(Y)

    if Y in evidence:
        prob = node.probability(evidence[Y], evidence)
        return prob * _enumerate_all(network, rest, evidence)
    else:
        total = 0.0
        for y_val in node.states:
            extended = dict(evidence)
            extended[Y] = y_val
            prob = node.probability(y_val, extended)
            total += prob * _enumerate_all(network, rest, extended)
        return total
