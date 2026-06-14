import re
import os
from typing import OrderedDict
from .logger import log_implication_graph_computation


def ensure_tex_file(file_path):
    if not file_path.endswith(".tex"):
        return file_path + ".tex"
    return file_path


def find_ref_arguments(text, cfg):
    unflattened_refs = []
    for cmd in cfg["ref_commands"]:
        unflattened_refs += re.findall(cmd + r'\{([^}]+)\}', text)

    refs = []
    for ref in unflattened_refs:
        refs += ref.split(",")

    return refs


def print_label_not_found_warning(obj, label_id):
    print(f"[impbot] Warning: {str(obj)} references "
          f"{label_id} which was not found, skipped.")


class TexLine:
    def __init__(self, text, file_path, number, cfg):
        # remove everything that is commented
        text = re.sub(r'(?<!\\)%.*', '', text)
        self.text = text
        self.number = number
        self.env = None
        self.cfg = cfg
        self.proof_of = None
        self.file_path = file_path
        self.is_env_start = False
        self.is_env_end = False

        label_ids = re.findall(r'\\label\{([^}]+)\}', text)
        if label_ids:
            self.label_id = label_ids[0]
        else:
            self.label_id = None

        self.refs = find_ref_arguments(text, cfg)
        self._get_proof_of()

    def _get_proof_of(self):
        proof_argument = re.findall(
            r'\\begin\{proof\}\[([^]]+)\]',
            self.text)
        if proof_argument:
            proof_of = find_ref_arguments(proof_argument[0], self.cfg)
            if proof_of:
                self.proof_of = proof_of[0]
                if proof_of in self.refs:
                    self.refs.remove(proof_of)

    def __str__(self):
        return f"{self.file_path}[L{self.number}]"

    def __repr__(self):
        return self.__str__()

    def detailed_str(self):
        text_without_line_breaks = self.text.replace('\n', '')
        out = f"[L{self.number}]\t{text_without_line_breaks}"
        if self.label_id is not None:
            out += f"\n\tLabel: {self.label_id}"
        if self.refs:
            out += f"\n\tRefs: {self.refs}"
        if self.env:
            out += f"\n\tEnv: {self.env} is_env_start:{self.is_env_start}"
            out += f" is_env_end:{self.is_env_end}"
        if self.proof_of is not None:
            out += f"\n\tProof of: {self.proof_of}"
        return out


# convention:
# a parent of a node is a node that is referenced in its proof or statement
# a child of a result is any result that references this node
class Node:
    def __init__(self, line_number, file_path, label_id, env=None):
        self.line_number = line_number
        self.file_path = file_path
        self.label_id = label_id
        self.env = env
        self.parents = set()
        self.children = set()
        self.depth = None
        # lines of the proof of this node, if applicable. format: [a, b)
        self.proof_file_path = None
        self.proof_start = None
        self.proof_end = None
        self.env_end_idx = None

    def __str__(self):
        return f"Node({self.label_id})"

    def __repr__(self):
        return self.__str__()

    def detailed_str(self):
        out = f"{self.file_path}[L{self.line_number}]"
        out += f"\n\tLabel id: {self.label_id}\tEnv: {self.env}"
        out += f"\tDepth: {self.depth}"
        if self.proof_start is not None:
            out += f"\n\tProof Interval: [{self.proof_start}, {self.proof_end})"
        if self.proof_file_path is not None:
            out += f"\n\tProof File: {self.proof_file_path}"
        if self.env_end_idx is not None:
            out += f"\n\tEnv End Line: {self.env_end_idx + 1}"
        if self.parents not in (None, set()):
            out += f"\n\tParents: {self.parents}"
        if self.children not in (None, set()):
            out += f"\n\tChildren: {self.children}"
        return out


class TexFile:
    def __init__(self, file_path, cfg, main_folder=None):
        self.file_path = ensure_tex_file(file_path)
        self.local_folder = os.path.dirname(self.file_path)
        self.main_folder = self.local_folder if main_folder is None \
            else main_folder
        self.lines = []
        self.cfg = cfg
        with open(self.file_path, "r") as f:
            for i, line_str in enumerate(f, start=1):
                self.lines.append(TexLine(
                    line_str, self.file_path, i, self.cfg))

        self._get_envs()
        self.nodes = OrderedDict()
        for line in self.lines:
            if line.label_id is not None:
                self.nodes[line.label_id] = Node(
                    line.number, self.file_path, line.label_id, line.env)

        self.children_file_paths = self._get_children_file_paths()

    def _get_envs(self):
        # determines the (innermost) environment for each line
        env_stack = []
        for line in self.lines:
            env_start = re.findall(r'\\begin\{([^}]+)\}', line.text)
            if env_start:
                line.is_env_start = True
            env_stack += env_start
            env_end = re.findall(r'\\end\{([^}]+)\}', line.text)
            line.env = env_stack[-1] if env_stack else None
            if env_end:
                line.is_env_end = True
                while env_end and env_stack[-1] == env_end[0]:
                    env_stack.pop()
                    env_end.pop(0)

    def _get_children_file_paths(self):
        # compute the paths of files that are
        # included, inputted, or sub-imported in the current file
        children_file_paths = []
        for line in self.lines:
            include_paths = re.findall(
                r'\\(?:include|input)\{([^}]+)\}', line.text)

            children_file_paths += [
                os.path.join(self.main_folder, ensure_tex_file(p))
                for p in include_paths
            ]

            relative_sub_import_paths = re.findall(
                r'\\subimport\{([^}]+)\}\{([^}]+)\}', line.text)

            children_file_paths += [
                os.path.join(self.local_folder, folder, ensure_tex_file(file))
                for (folder, file) in relative_sub_import_paths
            ]

        return children_file_paths

    def print_lines(self):
        s = ""
        for line in self.lines:
            s += str(line)
        print(s)


def compute_implication_graph(main_tex_file, cfg, log=False):
    r"""
    Reads the `main_tex_file` and creates an `OrderedDict` of the form
    `[(node_label_id: str, Node: node)]` with each node corresponding to a
    statement in the latex project, with assigned attributes including
        - `node.parents`: set of node ids which are referenced by `node`
        - `node.children`: set of node ids which reference `node`
    """
    main_tex_file = TexFile(main_tex_file, cfg)
    tex_files = OrderedDict([(main_tex_file.file_path, main_tex_file)])
    children_file_paths = main_tex_file.children_file_paths

    while children_file_paths:  # visit all sub-files
        child_file_path = children_file_paths.pop(0)
        if not os.path.isfile(child_file_path):
            print("[impbot] Warning: could not find "
                  f"{child_file_path}, skipping this file.")
            continue
        child_tex_file = TexFile(child_file_path, cfg,
                                 main_folder=main_tex_file.main_folder)
        tex_files[child_tex_file.file_path] = child_tex_file
        children_file_paths += child_tex_file.children_file_paths

    nodes = OrderedDict()
    for tex_file in tex_files.values():
        nodes.update(tex_file.nodes)

    # go through lines, identify proofs which specify which statement they prove
    # for example \begin{proof}[Proof of Theorem 1]
    for tex_file in tex_files.values():
        for line in tex_file.lines:
            if line.env == 'proof' and line.proof_of is not None:
                if line.proof_of in nodes:
                    nodes[line.proof_of].proof_start = line.number
                    nodes[line.proof_of].proof_file_path = line.file_path
                else:
                    print_label_not_found_warning(line, line.proof_of)

    # go through nodes and find the start of their proof
    # then determine the parents of each node
    # (refs in the proof and statement)
    ignored_envs = [None, ""] + cfg["ignored_envs"]

    def clean_parent_candidates(node, candidates):
        # helper function to update the parents set with only node_ids
        # of known nodes with non-ignored envs, and ignoring the child node
        cleaned_list = set()
        for candidate in candidates:
            if candidate not in nodes:
                print(f'[impbot] Warning: found unknown node {candidate} '
                      f'referenced by {str(node)}, skipped.')
                continue
            if (nodes[candidate].env not in ignored_envs
                    and candidate != node.label_id):
                cleaned_list.add(candidate)
        return cleaned_list

    for node in nodes.values():
        if node.env in cfg["envs_with_proofs"]:
            node_parents = set()
            max_dist = cfg["max_proof_distance"]
            node_tex_file = tex_files[node.file_path]

            if node.proof_start is None:  # determine it within the node's file
                node.proof_file_path = node.file_path
                line_idx = node.line_number - 1
                node.env_end_idx = None
                encountered_other_env_with_proof = False
                # search for the end of the statement and
                # for the start of the proof
                while line_idx < len(node_tex_file.lines):
                    # changed to another env:
                    # mark the end of the node's env
                    if (node.env_end_idx is None
                            and node_tex_file.lines[line_idx].env == node.env
                            and node_tex_file.lines[line_idx].is_env_end):
                        node.env_end_idx = line_idx - 1
                    if node_tex_file.lines[line_idx].env == 'proof':
                        break
                    # we are beyond the end of the node's env and found another
                    # env with proof: give up on looking for a proof
                    if (node.env_end_idx is not None
                        and node.env_end_idx < line_idx
                        and node_tex_file.lines[line_idx].is_env_start
                        and node_tex_file.lines[line_idx].env
                            in cfg["envs_with_proofs"]):
                        encountered_other_env_with_proof = True
                    line_idx += 1

                if (node.env_end_idx is None
                        or line_idx > node.env_end_idx + max_dist
                        or line_idx >= len(node_tex_file.lines)
                        or encountered_other_env_with_proof):
                    node.proof_start = None
                    print(
                        f"[impbot] Warning: could not find a proof for {node}.")
                else:
                    node.proof_start = line_idx

            # go through the node's proof and add parents
            if node.proof_start is not None:
                line_idx = node.proof_start
                proof_file = tex_files[node.proof_file_path]
                while (line_idx < len(proof_file.lines)
                        and r"end{proof}" not in
                        proof_file.lines[line_idx].text):
                    node_parents.update(clean_parent_candidates(
                        node, proof_file.lines[line_idx].refs))
                    line_idx += 1
                node.proof_end = line_idx - 1

            # go through the node's statement and add parents
            line_idx = node.line_number - 1
            while (line_idx < len(node_tex_file.lines)
                    and node_tex_file.lines[line_idx].env == node.env):
                node_parents.update(clean_parent_candidates(
                    node, node_tex_file.lines[line_idx].refs))
                line_idx += 1

            node.parents = node_parents

    # remove nodes with empty envs (likely sections) or ignored envs
    nodes = OrderedDict([
        (k, node) for (k, node) in nodes.items()
        if node.env not in ignored_envs])

    # determine children for each node using parents
    for node in nodes.values():
        node.children = set()
    for node in nodes.values():
        for parent_label_id in node.parents:
            nodes[parent_label_id].children.add(node.label_id)

    # compute node depths, nodes without parents have depth 0
    def dfs(node, depth):  # depth-first search
        if node.depth is None:
            node.depth = depth
        else:
            depth = max(depth, node.depth)
            node.depth = depth
        for child_id in node.children:
            dfs(nodes[child_id], depth + 1)

    for node in nodes.values():
        if node.parents == set():
            dfs(node, 0)

    node_to_node_idx = {node: idx for idx, node in enumerate(nodes.values())}

    if log:
        log_implication_graph_computation(tex_files, nodes)

    return nodes, node_to_node_idx
