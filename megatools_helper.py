"""
Helper module for locating bundled megatools executables.
Works both in development and when bundled with PyInstaller.
Cross-platform: supports Windows, Linux, and macOS.
On Linux, megatools may be split into megareg, megadf, megals, etc.
"""
import os
import sys
import subprocess
import platform
import shutil
import logging

logger = logging.getLogger(__name__)

if platform.system() == 'Windows':
    CREATION_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    CREATION_FLAGS = 0

MEGATOOLS_CMD_MAP = {
    "reg": "megareg",
    "df": "megadf",
    "ls": "megals",
    "dl": "megadl",
    "put": "megaput",
    "get": "megaget",
    "mkdir": "megamkdir",
    "rm": "megarm",
    "cp": "megacopy",
}

def _find_unified_megatools():
    """Try to find the unified megatools binary."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    system = platform.system()

    # Check bundled megatools directory (various structures)
    candidates = []
    if system == 'Windows':
        candidates = [
            os.path.join(base_path, "megatools", "megatools.exe"),
            os.path.join(base_path, "megatools", "megatools-1.11.3.20250401-win64", "megatools.exe"),
            os.path.join(base_path, "megatools-1.11.3.20250401-win64", "megatools.exe"),
        ]
    else:
        candidates = [
            os.path.join(base_path, "megatools", "megatools"),
            "/usr/bin/megatools",
            "/usr/local/bin/megatools",
            "/opt/homebrew/bin/megatools",
        ]
    
    for c in candidates:
        if os.path.isfile(c):
            return c

    system_path = shutil.which("megatools")
    if system_path:
        return system_path

    return None

def _find_split_binary(subcmd):
    """Find the split binary for a subcommand (e.g. 'reg' -> 'megareg')."""
    split_name = MEGATOOLS_CMD_MAP.get(subcmd)
    if not split_name:
        return None

    # Check PyInstaller bundle directory
    try:
        meipass = sys._MEIPASS
        bundled = os.path.join(meipass, "megatools", f"{split_name}.exe")
        if os.path.isfile(bundled):
            return bundled
    except AttributeError:
        pass

    # Check local megatools directory
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "megatools", f"{split_name}.exe")
    if os.path.isfile(local):
        return local

    system_path = shutil.which(split_name)
    if system_path:
        return system_path

    for base in ["/usr/bin", "/usr/local/bin", "/opt/homebrew/bin"]:
        candidate = os.path.join(base, split_name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None

def get_megatools_path():
    """
    Get the path to the megatools executable.
    Falls back to system PATH.
    """
    unified = _find_unified_megatools()
    if unified:
        return unified
    return "megatools"

def get_megatools_command(args, **kwargs):
    """
    Resolve the correct binary for a megatools subcommand.
    
    If unified megatools exists, returns [megatools, subcmd, ...rest].
    If split binaries exist (Linux), returns [megareg, ...rest] or [megadf, ...rest].
    
    Args:
        args: List like ['reg', '--scripted', '--register', ...] or ['df', '-u', ...]
        **kwargs: Passed to run_megatools_command
    
    Returns:
        subprocess.CompletedProcess
    """
    unified = _find_unified_megatools()
    
    if unified and os.path.isfile(unified):
        full_args = [unified] + args
        return run_megatools_command_raw(full_args, **kwargs)
    
    if args and args[0] in MEGATOOLS_CMD_MAP:
        split_bin = _find_split_binary(args[0])
        if split_bin:
            full_args = [split_bin] + args[1:]
            return run_megatools_command_raw(full_args, **kwargs)
    
    full_args = ["megatools"] + args
    return run_megatools_command_raw(full_args, **kwargs)

def run_megatools_command(args, **kwargs):
    """
    Run a megatools command. Handles both unified and split binary layouts.
    Supports proxy rotation if enabled.
    
    Args:
        args: List of command arguments. First element is the subcommand
              (e.g., ['reg', '--scripted', '--register', ...])
        **kwargs: Additional arguments to pass to subprocess.run
    
    Returns:
        subprocess.CompletedProcess
    """
    unified = _find_unified_megatools()
    
    if unified:
        full_args = [unified] + args
    elif args and args[0] in MEGATOOLS_CMD_MAP:
        split_bin = _find_split_binary(args[0])
        if split_bin:
            full_args = [split_bin] + args[1:]
        else:
            full_args = ["megatools"] + args
    else:
        full_args = ["megatools"] + args
    
    return run_megatools_command_raw(full_args, **kwargs)

def run_megatools_command_raw(full_args, **kwargs):
    """Internal: run a fully resolved command."""
    if 'encoding' not in kwargs and 'universal_newlines' in kwargs:
        kwargs['encoding'] = 'utf-8'
    
    if 'creationflags' not in kwargs and CREATION_FLAGS:
        kwargs['creationflags'] = CREATION_FLAGS
    
    timeout = kwargs.pop('timeout', 60)

    try:
        return subprocess.run(full_args, **kwargs, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=full_args,
            returncode=1,
            stdout="",
            stderr=f"Error: Command timed out after {timeout} seconds."
        )
    except FileNotFoundError:
        logger.error(f"megatools binary not found: {full_args[0]}")
        return subprocess.CompletedProcess(
            args=full_args,
            returncode=1,
            stdout="",
            stderr=f"Error: '{full_args[0]}' not found. Install megatools: sudo apt-get install megatools"
        )

def is_megatools_available():
    """
    Check if megatools binary is available and executable.
    
    Returns:
        tuple: (bool, str) - (available, path_or_error_message)
    """
    unified = _find_unified_megatools()
    if unified:
        try:
            result = subprocess.run(
                [unified, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                creationflags=CREATION_FLAGS if platform.system() == 'Windows' else 0,
            )
            if result.returncode == 0:
                return True, unified
            else:
                return False, f"megatools at '{unified}' returned error code {result.returncode}"
        except Exception as e:
            return False, f"Error checking megatools: {e}"
    
    for subcmd in ['reg', 'df', 'ls']:
        split_bin = _find_split_binary(subcmd)
        if split_bin:
            try:
                result = subprocess.run(
                    [split_bin, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                )
                if result.returncode == 0:
                    return True, f"Split binaries at: {os.path.dirname(split_bin)}"
            except Exception:
                pass
    
    return False, "megatools not found. Install: sudo apt-get install megatools"
