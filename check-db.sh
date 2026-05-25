#!/bin/bash
# 检查并修复 Gateway 数据库

STATE_DB="$HOME/.hermes/state.db"
BACKUP_DB="$HOME/.hermes/state.db.backup"

echo "Checking Gateway database health..."

# 检查数据库是否存在
if [ ! -f "$STATE_DB" ]; then
    echo "Database not found, will be created by Gateway"
    exit 0
fi

# 检查数据库完整性
INTEGRITY=$(sqlite3 "$STATE_DB" "PRAGMA integrity_check;" 2>&1)

if [ "$INTEGRITY" = "ok" ]; then
    echo "Database is healthy"
    exit 0
fi

echo "Database is corrupted: $INTEGRITY"

# 尝试从备份恢复
if [ -f "$BACKUP_DB" ]; then
    echo "Attempting to restore from backup..."
    
    # 检查备份是否健康
    BACKUP_INTEGRITY=$(sqlite3 "$BACKUP_DB" "PRAGMA integrity_check;" 2>&1)
    
    if [ "$BACKUP_INTEGRITY" = "ok" ]; then
        echo "Backup is healthy, restoring..."
        cp "$BACKUP_DB" "$STATE_DB"
        echo "Database restored from backup"
        exit 0
    else
        echo "Backup is also corrupted"
    fi
else
    echo "No backup found"
fi

# 无法恢复，删除损坏的数据库
echo "Removing corrupted database..."
mv "$STATE_DB" "$STATE_DB.corrupted.$(date +%s)" 2>/dev/null
rm -f "$STATE_DB-wal" "$STATE_DB-shm"

echo "Corrupted database removed, Gateway will create a new one"
exit 0
