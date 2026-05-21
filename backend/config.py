"""
Hermes Desktop - Configuration
"""
import os
import sys

# Hermes Agent venv directory
HERMES_VENV_DIR = os.environ.get(
    "HERMES_VENV_DIR",
    os.path.expanduser("~/.hermes/hermes-agent/venv"),
)

# Resolved hermes binary path
HERMES_BIN = os.path.join(HERMES_VENV_DIR, "bin", "hermes")

# Hermes Agent source directory
HERMES_AGENT_DIR = os.path.expanduser("~/.hermes/hermes-agent")

# Add Hermes Agent to Python path
if HERMES_AGENT_DIR not in sys.path:
    sys.path.insert(0, HERMES_AGENT_DIR)

# SQLite database path
DB_PATH = os.environ.get(
    "HERMES_DB_PATH",
    os.path.expanduser("~/.hermes/hermes-desktop.db"),
)

# Backend server
HOST = "0.0.0.0"
PORT = 8765
