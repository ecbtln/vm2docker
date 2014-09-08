__author__ = 'elubin'
from networkx import DiGraph
from networkx.algorithms.components.strongly_connected import strongly_connected_component_subgraphs
import logging


def filter_non_dependencies(nodes, get_deps_func):
    node_set = set(nodes)
    G = DiGraph()
    G.add_nodes_from(nodes)

    # process the edges based on the dependency function
    for n in G:
        deps = get_deps_func(n)
        for d in deps:
            if d in G:
                G.add_edge(n, d)



    # now filter the nodes and return them
    filtered_pkgs = {node for node, in_degree in G.in_degree_iter() if in_degree == 0}

    # now find any strongly connected components with size greater than 1
    # these will all have in degree > 0, but should still be included
    glist = [g for g in strongly_connected_component_subgraphs(G, copy=False) if g.number_of_nodes() > 1]

    for g in glist:
        # only counts if it was the original list
        nodes = [n for n in g.nodes() if n in node_set]
        if len(nodes) > 0:
            logging.debug('Strongly connected component: %s' % repr(nodes))
            for n in nodes:
                filtered_pkgs.add(n)

    return filtered_pkgs

