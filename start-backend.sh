#!/bin/bash
set -e
echo "Starting Hermes Backend..."
cd /mnt/d/soso/projects/hermes-desktop/backend
echo "Current directory: $(pwd)"
echo "Python path: .venv/bin/python"
.venv/bin/python main.py
echo "Backend exited."
read -p "Press Enter to close..."
