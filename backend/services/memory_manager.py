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
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
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
                    cursor.execute(f"DELETE FROM {table_name}")
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
