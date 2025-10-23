#!/usr/bin/env python3
"""
GAL CLI entry point for python -m gal.cli
"""

import sys
from pathlib import Path

# Add parent directory to sys.path to import gal-cli
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import and run the CLI
if __name__ == "__main__":
    # Import from gal-cli.py
    import importlib.util

    cli_path = parent_dir / "gal-cli.py"
    spec = importlib.util.spec_from_file_location("gal_cli", cli_path)
    gal_cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gal_cli)

    # Run the CLI
    gal_cli.cli()
