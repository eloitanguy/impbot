import yaml
import importlib.resources
import shutil


def latex_command_escape(cmd):
    # transforms a command name (eg cref)
    # into a regex-escaped version (eg \\cref)
    return r"\\" + cmd


def copy_default_config(target_path, verbose=False):
    default_cfg_path = importlib.resources.files(
        "impbot").joinpath("impbot_default_cfg.yaml")
    shutil.copy2(default_cfg_path, target_path)
    if verbose:
        print(f"[impbot] Copied default config to {target_path}.")


def load_config(config_path, verbose=False):
    if verbose:
        print(f"[impbot] Loading configuration from {config_path}.")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    config["ref_commands"] = [
        latex_command_escape(cmd) for cmd in config["ref_commands"]]
    return config
