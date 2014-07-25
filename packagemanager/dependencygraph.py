__author__ = 'elubin'
from networkx import DiGraph


def filter_non_dependencies(nodes, get_deps_func):
    G = DiGraph()
    G.add_nodes_from(nodes)

    # process the edges based on the dependency function
    for n in G:
        deps = get_deps_func(n)
        for d in deps:
            if d in G:
                G.add_edge(n, d)


    # now filter the nodes and return them
    return [node for node, in_degree in G.in_degree_iter() if in_degree == 0]