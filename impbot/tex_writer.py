def compute_tikz_code_string(nodes_dict, coords, node_to_node_idx, cfg,
                             impbot_version):
    nodes = nodes_dict.values()
    if not nodes:
        print("[impbot] Fatal: could not parse any nodes, abort.")
        return ""
    s = r"% cspell:disable" + "\n"
    s += f"% Generated automatically by impBot {impbot_version}\n"
    s += "% Modifying this file runs the risk of losing your changes\n"
    for env, colour in cfg['env_colours'].items():
        s += r"\definecolor{impBot_" + env + r"}{HTML}{" \
            + colour + r"}" + "\n"
    s += r"""
\tikzset{
  default/.style={
    rectangle,
    rounded corners,
    draw=impBot_default,
    fill=impBot_default!10!white,
    align=center,
    inner sep=2pt,
    outer sep=0pt,"""
    s += "\n" + r"    node font=\fontsize{" + str(cfg['fontsize']) + "}{"
    s += str(cfg['fontsize']) + r"}\selectfont," + "\n"
    s += r"""  },
  arrow/.style={
    thick,
    draw=impBot_arrow,
    shorten >=2pt,
    shorten <=2pt,
"""
    s += r"    line width=" + cfg['edge_thickness'] + "\n"
    s += r"""  },
}

\tikzset{
  theorem/.style={
    default,
    draw=impBot_theorem,
    double=impBot_theorem!50!white,
    fill=impBot_theorem!10!white,
  },
  definition/.style={
    default,
    rounded corners=0pt,
    draw=impBot_definition,
    fill=impBot_definition!10!white,
  },
  assumption/.style={
    default,
    rounded corners=0pt,
    draw=impBot_assumption,
    fill=impBot_assumption!10!white,
  },
  proposition/.style={
    default,
    draw=impBot_proposition,
    fill=impBot_proposition!10!white,
  },
  prop/.style={
    default,
    draw=impBot_prop,
    fill=impBot_prop!10!white,
  },
  corollary/.style={
    default,
    draw=impBot_corollary,
    fill=impBot_corollary!10!white,
  },
  lemma/.style={
    default,
    densely dashed,
    draw=impBot_lemma,
    fill=impBot_lemma!10!white,
  },
}"""
    s += "\n"
    s += r"\begin{center}\begin{tikzpicture}[xscale=" \
        + str(cfg['xscale']) + ", yscale=" \
        + str(cfg['yscale']) + "]\n"
    max_depth = max(node.depth for node in nodes)

    def cvrt(node_label_id):
        tikz_node_id = node_label_id.replace(":", "COLON")
        return tikz_node_id

    # draw all nodes depth by depth
    for depth in range(0, max_depth + 1):
        s += f"  % nodes: depth {depth}\n"
        for node in nodes:
            node_idx = node_to_node_idx[node]
            if node.depth == depth:
                s += f"  % {node.env} {node.label_id} at {node.file_path}"
                s += f"[L{node.line_number}]\n"
                env = node.env if node.env in cfg['env_colours'] else 'default'
                s += r"  \node[" + env + r"] (" + cvrt(node.label_id) + r")" \
                    + r" at (" + str(coords[node_idx][0]) + "," \
                    + str(coords[node_idx][1]) + r")" \
                    + r" {\Cref{" + node.label_id + "}};\n\n"
        s += "\n"

    # draw all arrows
    s += "  % arrows\n"
    s += r"  \begin{pgfonlayer}{background}" + "\n\n"
    for node in nodes:
        if node.children not in [None, set()]:
            n_children = float(len(node.children))
            s += r"    \begin{scope}[transparency group, opacity="\
                + str(1 / (n_children ** .5)) + r"]" + "\n"
            for child_id in node.children:
                s += r"      \draw[arrow, " + f"{node.env}] (" \
                    + cvrt(node.label_id) + ".east)" \
                    + r" -- (" + cvrt(child_id) + ".west);\n"
            s += r"    \end{scope}" + "\n\n"

    s += r"  \end{pgfonlayer}" + "\n"
    s += r"\end{tikzpicture}\end{center}"
    return s


def write_tikz_tex_file(tikz_code_string, file_path):
    with open(file_path, "w") as f:
        f.write(tikz_code_string)


def write_impbot_requirements_tex_file(file_path, impbot_version):
    s = ""
    s += f"% Generated automatically by impBot {impbot_version}\n"
    s += "% Modifying this file runs the risk of losing your changes\n"
    s = r"""\PassOptionsToPackage{svgnames}{xcolor}
\RequirePackage{xcolor}
\RequirePackage{tikz}
\usetikzlibrary{backgrounds}
\RequirePackage[nameinlink]{cleveref}
    """
    with open(file_path, "w") as f:
        f.write(s)
