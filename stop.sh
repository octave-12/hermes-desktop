#!/bin/bash
# 优雅停止 Hermes 服务

echo "[1/3] Stopping Frontend..."
pkill -TERM -f "pnpm run dev" 2>/dev/null
pkill -TERM -f "electron" 2>/dev/null
sleep 1

echo "[2/3] Stopping Backend..."
pkill -TERM -f "python main.py" 2>/dev/null
sleep 2

echo "[3/3] Stopping Gateway gracefully..."
# 发送 SIGTERM 让 Gateway 优雅关闭
pkill -TERM -f "hermes gateway" 2>/dev/null

# 等待最多 5 秒
for i in {1..5}; do
    if ! pgrep -f "hermes gateway" > /dev/null; then
        echo "Gateway stopped gracefully"
        break
    fi
    echo "Waiting for Gateway to stop... ($i/5)"
    sleep 1
done

# 如果还在运行，强制终止
if pgrep -f "hermes gateway" > /dev/null; then
    echo "Gateway not responding, force killing..."
    pkill -9 -f "hermes gateway" 2>/dev/null
    sleep 1
fi

echo "All services stopped"
