#!/bin/bash
# 优雅停止 Hermes 服务（不杀 Gateway、龙神、Ollama）

echo "[1/2] Stopping Frontend..."
pkill -TERM -f "pnpm run dev" 2>/dev/null
pkill -TERM -f "electron" 2>/dev/null
sleep 1

echo "[2/2] Stopping Backend..."
pkill -TERM -f "python.*hermes-desktop.*main.py" 2>/dev/null
sleep 2

echo "Hermes services stopped (Gateway, Ollama, Dragon Server kept running)"
