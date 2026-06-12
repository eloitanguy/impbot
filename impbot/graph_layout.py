import numpy as np


def compute_implication_graph_layout(nodes_dict, layout='vertical'):
    coords = np.zeros((len(nodes_dict.values()), 2))
    for node_idx, node in enumerate(nodes_dict.values()):
        coords[node_idx, 0] = -node_idx  # x = index of discovery
        coords[node_idx, 1] = node.depth  # y = depth in the graph
    if layout == 'vertical':
        coords = coords[:, [1, 0]]  # swap x and y for vertical layout
    return coords
