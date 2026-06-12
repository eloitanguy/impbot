from .tex_parser import compute_implication_graph
from .graph_layout import compute_implication_graph_layout
from .tex_writer import (
    compute_tikz_code_string, write_tikz_tex_file, write_impbot_requirements_tex_file)
from .config_handler import load_config, copy_default_config
import argparse
import os
from importlib.metadata import version
from time import time


def main():
    v = version("impbot")
    parser = argparse.ArgumentParser(
        description="Generate a TikZ graph of the implications"
                    "in a LaTeX document.",
        usage="impbot <main_tex_file.tex>")
    parser.add_argument(
        'input', type=str,
        help='Path to the input .tex file')
    parser.add_argument(
        '--version', '--v', action='version',
        version="impbot " + v)
    args = parser.parse_args()

    t0 = time()
    print(f"Running impbot version {v}...")

    main_tex_file = args.input

    if not os.path.isfile(main_tex_file):
        print(f"Error: could not find {main_tex_file}.")
        return

    # determine and create impbot output folder
    main_tex_folder = os.path.dirname(main_tex_file)
    impbot_folder = os.path.join(main_tex_folder, "impbot")
    if not os.path.isdir(impbot_folder):
        print(f"[impbot] Could not find {impbot_folder} folder, "
              "created an empty one.")
        os.mkdir(impbot_folder)

    tikz_file_path = os.path.join(
        impbot_folder, "implication_graph.tex")

    # write a default config file or read an existing one
    cfg_path = os.path.join(impbot_folder, "impbot_cfg.yaml")
    if not os.path.isfile(cfg_path):
        copy_default_config(cfg_path, verbose=True)
    cfg = load_config(cfg_path, verbose=True)

    # write the impbot_requirements.tex file
    write_impbot_requirements_tex_file(
        os.path.join(impbot_folder, "impbot_requirements.tex"), v)

    print("[impbot] Computing implication graph...")
    nodes, node_to_node_idx = \
        compute_implication_graph(main_tex_file, cfg)
    print("[impbot] Computing graph layout...")
    coords = compute_implication_graph_layout(nodes)
    print("[impbot] Generating TikZ code...")
    tikz_code_string = compute_tikz_code_string(
        nodes, coords, node_to_node_idx, cfg,
        impbot_version=v)
    print(f"[impbot] Writing TikZ code to {tikz_file_path}...")
    write_tikz_tex_file(tikz_code_string, tikz_file_path)
    dt = time() - t0
    print(f"[impbot] Finished in {1000 * dt:.2f}ms")
