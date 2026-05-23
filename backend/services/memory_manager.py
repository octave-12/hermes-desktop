"""
Memory Manager - Read/Write Hermes Agent memory files
"""
import os
from typing import Dict, List, Optional
from pathlib import Path


class MemoryManager:
    """Manage Hermes Agent memory files."""
    
    def __init__(self):
        self.hermes_home = os.path.expanduser("~/.hermes")
        self.memories_dir = os.path.join(self.hermes_home, "memories")
        self.memory_db = os.path.join(self.hermes_home, "memory.db")
    
    def get_memory_types(self) -> List[Dict]:
        """Get list of memory types with metadata."""
        types = []
        
        # MEMORY.md - Project memory
        memory_md = os.path.join(self.memories_dir, "MEMORY.md")
        types.append({
            "id": "project",
            "name": "项目记忆",
            "file": "MEMORY.md",
            "path": memory_md,
            "exists": os.path.exists(memory_md),
            "size": os.path.getsize(memory_md) if os.path.exists(memory_md) else 0,
            "description": "项目相关的长期记忆，如设定、大纲、伏笔等"
        })
        
        # USER.md - User memory
        user_md = os.path.join(self.memories_dir, "USER.md")
        types.append({
            "id": "user",
            "name": "用户记忆",
            "file": "USER.md",
            "path": user_md,
            "exists": os.path.exists(user_md),
            "size": os.path.getsize(user_md) if os.path.exists(user_md) else 0,
            "description": "用户个人信息和偏好"
        })
        
        # SOUL.md - Agent personality (optional)
        soul_md = os.path.join(self.hermes_home, "SOUL.md")
        types.append({
            "id": "soul",
            "name": "Agent 人格",
            "file": "SOUL.md",
            "path": soul_md,
            "exists": os.path.exists(soul_md),
            "size": os.path.getsize(soul_md) if os.path.exists(soul_md) else 0,
            "description": "Agent 的人格设定和行为准则"
        })
        
        # memory.db - Database
        types.append({
            "id": "database",
            "name": "记忆数据库",
            "file": "memory.db",
            "path": self.memory_db,
            "exists": os.path.exists(self.memory_db),
            "size": os.path.getsize(self.memory_db) if os.path.exists(self.memory_db) else 0,
            "description": "结构化记忆数据（SQLite）"
        })
        
        # Main application database (hermes.db)
        from config import DB_PATH
        types.append({
            "id": "maindb",
            "name": "应用主数据库",
            "file": "hermes.db",
            "path": DB_PATH,
            "exists": os.path.exists(DB_PATH),
            "size": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
            "description": "应用数据（会话、消息、配置）"
        })
        
        return types
    
    def get_memory_content(self, memory_id: str) -> Optional[str]:
        """Get content of a memory file."""
        types = self.get_memory_types()
        memory = next((m for m in types if m["id"] == memory_id), None)
        
        if not memory or not memory["exists"]:
            return None
        
        if memory_id == "database":
            # Return database info instead of binary content
            import sqlite3
            try:
                conn = sqlite3.connect(memory["path"])
                cursor = conn.cursor()
                
                # Get tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                info = f"# 记忆数据库\n\n"
                info += f"文件: {memory['path']}\n"
                info += f"大小: {memory['size']} bytes\n\n"
                info += "## 表结构\n\n"
                
                for (table_name,) in tables:
                    # Whitelist validate table name (alphanumeric and underscore only)
                    if not table_name.replace('_', '').isalnum():
                        continue
                    cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
                    count = cursor.fetchone()[0]
                    info += f"- **{table_name}**: {count} 条记录\n"
                
                conn.close()
                return info
            except Exception as e:
                return f"读取数据库失败: {str(e)}"
        
        # Read text files
        try:
            with open(memory["path"], "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"读取失败: {str(e)}"
    
    def get_memory_entries(self, memory_id: str) -> List[Dict]:
        """Get memory entries (split by § separator)."""
        content = self.get_memory_content(memory_id)
        if not content:
            return []
        
        if memory_id == "database":
            return [{"index": 0, "content": content, "raw": content}]
        
        # Split by § separator
        entries = []
        parts = content.split("§")
        
        for i, part in enumerate(parts):
            part = part.strip()
            if part:
                entries.append({
                    "index": i,
                    "content": part,
                    "raw": part
                })
        
        return entries
    
    def get_db_entries(self, category: str = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get entries from SQLite memory database."""
        import sqlite3
        import json
        
        if not os.path.exists(self.memory_db):
            return []
        
        try:
            conn = sqlite3.connect(self.memory_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if category:
                cursor.execute(
                    "SELECT * FROM memories WHERE category = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (category, limit, offset)
                )
            else:
                cursor.execute(
                    "SELECT * FROM memories ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            
            rows = cursor.fetchall()
            entries = []
            for row in rows:
                entries.append({
                    "id": row["id"],
                    "content": row["content"],
                    "category": row["category"],
                    "importance": row["importance"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            
            conn.close()
            return entries
        except Exception as e:
            print(f"[ERROR] Failed to get db entries: {e}")
            return []
    
    def get_db_categories(self) -> List[Dict]:
        """Get all categories with count."""
        import sqlite3
        
        if not os.path.exists(self.memory_db):
            return []
        
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()
            cursor.execute("SELECT category, COUNT(*) as count FROM memories GROUP BY category ORDER BY count DESC")
            rows = cursor.fetchall()
            conn.close()
            return [{"category": r[0], "count": r[1]} for r in rows]
        except Exception as e:
            print(f"[ERROR] Failed to get categories: {e}")
            return []
    
    def add_db_entry(self, content: str, category: str = "general", importance: int = 1, tags: List[str] = None) -> Optional[int]:
        """Add a new entry to SQLite memory database."""
        import sqlite3
        import json
        
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memories (content, category, importance, tags) VALUES (?, ?, ?, ?)",
                (content, category, importance, json.dumps(tags or []))
            )
            entry_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return entry_id
        except Exception as e:
            print(f"[ERROR] Failed to add db entry: {e}")
            return None
    
    def update_db_entry(self, entry_id: int, content: str = None, category: str = None, importance: int = None, tags: List[str] = None) -> bool:
        """Update an entry in SQLite memory database."""
        import sqlite3
        import json
        
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if content is not None:
                updates.append("content = ?")
                params.append(content)
            if category is not None:
                updates.append("category = ?")
                params.append(category)
            if importance is not None:
                updates.append("importance = ?")
                params.append(importance)
            if tags is not None:
                updates.append("tags = ?")
                params.append(json.dumps(tags))
            
            if not updates:
                conn.close()
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(entry_id)
            
            cursor.execute(f"UPDATE memories SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to update db entry: {e}")
            return False
    
    def delete_db_entry(self, entry_id: int) -> bool:
        """Delete an entry from SQLite memory database."""
        import sqlite3
        
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete db entry: {e}")
            return False
    
    def delete_memory_entry(self, memory_id: str, entry_index: int) -> bool:
        """Delete a single memory entry by index."""
        types = self.get_memory_types()
        memory = next((m for m in types if m["id"] == memory_id), None)
        
        if not memory or not memory["exists"]:
            return False
        
        if memory_id == "database":
            return False
        
        try:
            with open(memory["path"], "r", encoding="utf-8") as f:
                content = f.read()
            
            parts = content.split("§")
            
            if entry_index < 0 or entry_index >= len(parts):
                return False
            
            # Remove the entry
            parts.pop(entry_index)
            
            # Reconstruct content
            new_content = "§".join(parts)
            
            with open(memory["path"], "w", encoding="utf-8") as f:
                f.write(new_content)
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete memory entry: {e}")
            return False
    
    def update_memory_content(self, memory_id: str, content: str) -> bool:
        """Update content of a memory file."""
        types = self.get_memory_types()
        memory = next((m for m in types if m["id"] == memory_id), None)
        
        if not memory or memory_id == "database":
            return False
        
        try:
            os.makedirs(os.path.dirname(memory["path"]), exist_ok=True)
            with open(memory["path"], "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to update memory: {e}")
            return False
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory file."""
        types = self.get_memory_types()
        memory = next((m for m in types if m["id"] == memory_id), None)
        
        if not memory or not memory["exists"]:
            return False
        
        if memory_id == "database":
            # Don't delete database, just clear it
            try:
                import sqlite3
                conn = sqlite3.connect(memory["path"])
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                for (table_name,) in tables:
                    # Whitelist validate table name
                    if not table_name.replace('_', '').isalnum():
                        continue
                    cursor.execute(f"DELETE FROM [{table_name}]")
                conn.commit()
                conn.close()
                return True
            except:
                return False
        
        try:
            os.remove(memory["path"])
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete memory: {e}")
            return False


memory_manager = MemoryManager()
