from importlib.metadata import version
import os


def log_implication_graph_computation(tex_files, nodes):
    v = version("impbot")
    log = f"impbot v{v} log file: execution on "
    log += list(tex_files.values())[0].file_path
    log += """\n\n
-----------------------------
- .tex file parsing results -
-----------------------------\n\n"""
    for tex_file in tex_files.values():
        log += f"Found {tex_file.file_path}\n"
        for line in tex_file.lines:
            log += line.detailed_str() + "\n"
    log += """\n\n
----------------
- parsed nodes -
----------------\n\n"""
    for node in nodes.values():
        log += node.detailed_str() + "\n"

    log_file_path = os.path.join(list(tex_files.values())[0].local_folder,
                                 'impbot/log.txt')
    with open(log_file_path, "w") as f:
        f.write(log)
