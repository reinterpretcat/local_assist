import sqlite3
from dataclasses import dataclass, asdict
import json
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class LLMSettings:
    """Settings specific to language model configuration."""

    system_prompt: Optional[str] = None
    model_id: Optional[str] = None
    temperature: Optional[float] = None
    num_ctx: Optional[int] = None
    num_predict: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "LLMSettings":
        """Create LLM settings from dictionary, handling missing fields."""
        if not data:
            return cls()
        return cls(
            system_prompt=data.get("system_prompt"),
            model_id=data.get("model_id"),
            temperature=data.get("temperature"),
            num_ctx=data.get("num_ctx"),
            num_predict=data.get("num_predict"),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values and returning None if all default."""
        non_default = {k: v for k, v in asdict(self).items() if v is not None}
        return non_default if non_default else None


class ChatSettings:
    """Manages chat-specific settings."""

    def __init__(self, markdown_enabled=True, replies_allowed=True, llm=LLMSettings()):
        self.markdown_enabled = markdown_enabled
        self.replies_allowed = replies_allowed
        self.llm: LLMSettings = llm
        # self._custom_settings: Dict[str, Any] = {}

    def to_dict(self) -> dict:
        """Convert settings to dictionary for serialization, excluding default values."""
        result = {}

        # Only include non-default values
        if not self.markdown_enabled:
            result["markdown_enabled"] = False
        if not self.replies_allowed:
            result["replies_allowed"] = False

        # Include LLM settings only if they differ from defaults
        llm_dict = self.llm.to_dict()
        if llm_dict:
            result["llm"] = llm_dict

        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ChatSettings":
        """Create settings from dictionary."""
        settings = cls()
        settings.markdown_enabled = data.get("markdown_enabled", True)
        settings.replies_allowed = data.get("replies_allowed", True)
        settings.llm = LLMSettings.from_dict(data.get("llm"))
        # settings._custom_settings = data.get("custom_settings", {})
        return settings

    def replace(self, **kwargs):
        # Create a new object with the specified updated attributes
        return ChatSettings(**{**self.__dict__, **kwargs})


class ChatHistoryDB:
    """SQLite database manager for chat history."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    parent_id INTEGER,
                    position INTEGER,
                    settings TEXT,
                    FOREIGN KEY (parent_id) REFERENCES nodes (id)
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    node_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    image_path TEXT,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes (id)
                )
            """
            )

            # Create root node if doesn't exist
            cursor = conn.execute("SELECT id FROM nodes WHERE parent_id IS NULL")
            if not cursor.fetchone():
                conn.execute(
                    "INSERT INTO nodes (name, type, parent_id) VALUES (?, ?, ?)",
                    ("/", "group", None),
                )


class ChatHistory:
    """Manages chat history using SQLite storage."""

    def __init__(self, db_path: str, default_prompt: Optional[str], history_sort=False):
        self.db = ChatHistoryDB(db_path)
        self.default_prompt = default_prompt
        self.history_sort = history_sort
        self.active_path: Optional[List[str]] = None

        # Cache for active chat messages
        self._active_messages: List[Dict[str, Any]] = []
        self._active_settings: Optional[ChatSettings] = None

        self.ensure_default_chat()

    def _get_node_id(self, path: List[str]) -> int:
        """Get node ID for given path."""
        with sqlite3.connect(self.db.db_path) as conn:
            current_id = conn.execute(
                "SELECT id FROM nodes WHERE parent_id IS NULL"
            ).fetchone()[0]

            for name in path:
                current_id = conn.execute(
                    "SELECT id FROM nodes WHERE parent_id = ? AND name = ?",
                    (current_id, name),
                ).fetchone()[0]

            return current_id

    def _load_active_chat(self):
        """Load active chat messages and settings into memory."""
        if not self.active_path:
            self._active_messages = []
            self._active_settings = ChatSettings()
            return

        node_id = self._get_node_id(self.active_path)

        with sqlite3.connect(self.db.db_path) as conn:
            # Load messages
            cursor = conn.execute(
                """
                SELECT role, content, image_path 
                FROM messages 
                WHERE node_id = ? 
                ORDER BY position
                """,
                (node_id,),
            )

            self._active_messages = [
                {
                    "role": role,
                    "content": content,
                    **({"image_path": img_path} if img_path else {}),
                }
                for role, content, img_path in cursor
            ]

            # Load settings
            settings_json = conn.execute(
                "SELECT settings FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()[0]

            self._active_settings = (
                ChatSettings.from_dict(json.loads(settings_json))
                if settings_json
                else ChatSettings()
            )

    def create_chat(
        self, name: str, parent_path: Optional[List[str]] = None
    ) -> List[str]:
        """Create a new chat at specified path."""
        parent_path = parent_path or []

        with sqlite3.connect(self.db.db_path) as conn:
            # Get parent node ID
            parent_id = self._get_node_id(parent_path)

            # Check if name exists
            exists = conn.execute(
                "SELECT 1 FROM nodes  WHERE parent_id = ? AND name = ?",
                (parent_id, name),
            ).fetchone()

            if exists:
                raise ValueError(
                    f"Item already exists at path: {'/'.join(parent_path)}/{name}"
                )

            # Create settings
            settings = ChatSettings()
            settings.llm.system_prompt = self.default_prompt

            # Insert new chat
            position = conn.execute(
                "SELECT COUNT(*) FROM nodes WHERE parent_id = ?", (parent_id,)
            ).fetchone()[0]

            cursor = conn.execute(
                """
                INSERT INTO nodes (name, type, parent_id, position, settings)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, "chat", parent_id, position, json.dumps(settings.to_dict())),
            )

            # Add welcome message
            conn.execute(
                """
                INSERT INTO messages (node_id, role, content, position)
                VALUES (?, ?, ?, ?)
                """,
                (cursor.lastrowid, "tool", "Welcome to your new chat!", 0),
            )

        return parent_path + [name]

    def append_message(self, role: str, content: str, image_path: Optional[str] = None):
        """Append message to active chat."""
        if not self.active_path:
            raise ValueError("No active chat selected")

        node_id = self._get_node_id(self.active_path)

        with sqlite3.connect(self.db.db_path) as conn:
            position = len(self._active_messages)
            conn.execute(
                """
                INSERT INTO messages (node_id, role, content, image_path, position)
                VALUES (?, ?, ?, ?, ?)
                """,
                (node_id, role, content, image_path, position),
            )

        # Update cache
        message = {"role": role, "content": content}
        if image_path:
            message["image_path"] = image_path
        self._active_messages.append(message)

    def set_active_chat(self, path: List[str]):
        """Set active chat by path."""
        self.active_path = path
        self._load_active_chat()

    def get_active_chat_messages(self) -> List[Dict]:
        """Get messages for an active chat."""
        return self.get_chat_messages(path=None)

    def get_chat_messages(
        self, path: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get messages for chat at specified path."""
        if path is None:
            return self._active_messages.copy()

        if path == self.active_path:
            return self._active_messages.copy()

        node_id = self._get_node_id(path)

        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT role, content, image_path 
                FROM messages 
                WHERE node_id = ? 
                ORDER BY position
                """,
                (node_id,),
            )

            return [
                {
                    "role": role,
                    "content": content,
                    **({"image_path": img_path} if img_path else {}),
                }
                for role, content, img_path in cursor
            ]

    def get_nodes(self, path: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Get all nodes at the specified path."""
        path = path or []
        parent_id = self._get_node_id(path)

        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT name, type 
                FROM nodes 
                WHERE parent_id = ?
                ORDER BY position
                """,
                (parent_id,),
            )

            nodes = [{"name": name, "type": node_type} for name, node_type in cursor]

            if self.history_sort:
                return sorted(
                    nodes, key=lambda x: (x["type"] != "group", x["name"].lower())
                )

            return nodes

    def create_group(
        self, name: str, parent_path: Optional[List[str]] = None
    ) -> List[str]:
        """Create a new group at specified path."""
        parent_path = parent_path or []

        with sqlite3.connect(self.db.db_path) as conn:
            parent_id = self._get_node_id(parent_path)

            # Check if name exists
            exists = conn.execute(
                "SELECT 1 FROM nodes  WHERE parent_id = ? AND name = ?",
                (parent_id, name),
            ).fetchone()

            if exists:
                raise ValueError(
                    f"Item already exists at path: {'/'.join(parent_path)}/{name}"
                )

            # Insert new group
            position = conn.execute(
                "SELECT COUNT(*) FROM nodes WHERE parent_id = ?", (parent_id,)
            ).fetchone()[0]

            conn.execute(
                """
                INSERT INTO nodes (name, type, parent_id, position)
                VALUES (?, ?, ?, ?)
                """,
                (name, "group", parent_id, position),
            )

        return parent_path + [name]

    def rename_node(self, old_path: List[str], new_name: str):
        """Rename group or chat at specified path."""
        with sqlite3.connect(self.db.db_path) as conn:
            node_id = self._get_node_id(old_path)
            parent_id = conn.execute(
                "SELECT parent_id FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()[0]

            # Check if new name exists in parent
            exists = conn.execute(
                "SELECT 1 FROM nodes  WHERE parent_id = ? AND name = ?",
                (parent_id, new_name),
            ).fetchone()

            if exists:
                raise ValueError(f"Item {new_name} already exists in this location")

            conn.execute("UPDATE nodes SET name = ? WHERE id = ?", (new_name, node_id))

        # Update active path if needed
        if self.active_path and old_path == self.active_path[: len(old_path)]:
            self.active_path = (
                old_path[:-1] + [new_name] + self.active_path[len(old_path) :]
            )

    def delete_node(self, path: List[str]):
        """Delete group or chat at specified path."""
        with sqlite3.connect(self.db.db_path) as conn:
            node_id = self._get_node_id(path)

            # Delete all descendant nodes and their messages recursively
            conn.executescript(
                f"""
                WITH RECURSIVE descendants(id) AS (
                    SELECT {node_id}
                    UNION ALL
                    SELECT n.id
                    FROM nodes n
                    JOIN descendants d ON n.parent_id = d.id
                )
                DELETE FROM messages WHERE node_id IN descendants;
                
                WITH RECURSIVE descendants(id) AS (
                    SELECT {node_id}
                    UNION ALL
                    SELECT n.id
                    FROM nodes n
                    JOIN descendants d ON n.parent_id = d.id
                )
                DELETE FROM nodes WHERE id IN descendants;
            """
            )

        # Reset active path if deleting active chat or its parent
        if self.active_path and path == self.active_path[: len(path)]:
            self.active_path = None
            self._active_messages = []
            self._active_settings = None

    def move_node(
        self,
        source_path: List[str],
        target_path: List[str],
        position: Optional[int] = None,
    ):
        """Move a node to a new location with optional position."""
        with sqlite3.connect(self.db.db_path) as conn:
            source_id = self._get_node_id(source_path)
            target_id = self._get_node_id(target_path)

            source_name = conn.execute(
                "SELECT name FROM nodes WHERE id = ?", (source_id,)
            ).fetchone()[0]

            # Check if name exists in target
            exists = conn.execute(
                "SELECT 1 FROM nodes  WHERE parent_id = ? AND name = ?",
                (target_id, source_name),
            ).fetchone()

            if exists:
                raise ValueError(
                    f"Item {source_name} already exists in target location"
                )

            if position is not None:
                # Update positions for reordering
                conn.execute(
                    """
                    UPDATE nodes 
                    SET position = position + 1
                    WHERE parent_id = ? AND position >= ?
                    """,
                    (target_id, position),
                )

                conn.execute(
                    """
                    UPDATE nodes 
                    SET parent_id = ?, position = ?
                    WHERE id = ?
                    """,
                    (target_id, position, source_id),
                )
            else:
                # Move to end of target
                new_position = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE parent_id = ?", (target_id,)
                ).fetchone()[0]

                conn.execute(
                    """
                    UPDATE nodes 
                    SET parent_id = ?, position = ?
                    WHERE id = ?
                    """,
                    (target_id, new_position, source_id),
                )

            # Update active path if needed
            if self.active_path and source_path == self.active_path[: len(source_path)]:
                self.active_path = (
                    target_path + [source_name] + self.active_path[len(source_path) :]
                )

    def get_chat_settings(self, path: Optional[List[str]] = None) -> ChatSettings:
        """Get settings for specified chat."""
        if path is None:
            if not self._active_settings:
                self._load_active_chat()
            return self._active_settings

        if path == self.active_path:
            return self._active_settings

        node_id = self._get_node_id(path)

        with sqlite3.connect(self.db.db_path) as conn:
            settings_json = conn.execute(
                "SELECT settings FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()[0]

            return ChatSettings.from_dict(
                json.loads(settings_json) if settings_json else {}
            )

    def set_chat_settings(
        self, settings: ChatSettings, path: Optional[List[str]] = None
    ):
        """Set settings for specified chat."""
        if path is None:
            path = self.active_path

        if not path:
            raise ValueError("No chat selected")

        node_id = self._get_node_id(path)

        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute(
                "UPDATE nodes SET settings = ? WHERE id = ?",
                (json.dumps(settings.to_dict()), node_id),
            )

        if path == self.active_path:
            self._active_settings = settings

    def append_message_partial(self, role: str, token: str, is_first_token: bool):
        """Append message token to active chat."""
        if is_first_token:
            self.append_message(role, "")
        else:
            if not self.active_path:
                raise ValueError("No active chat selected")

            node_id = self._get_node_id(self.active_path)
            last_position = len(self._active_messages) - 1

            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute(
                    """
                    UPDATE messages 
                    SET content = content || ?
                    WHERE node_id = ? AND position = ?
                    """,
                    (token, node_id, last_position),
                )

            # Update cache
            self._active_messages[-1]["content"] += token

    def get_last_message(self) -> Dict[str, Any]:
        """Returns last message in the active chat."""
        if not self._active_messages:
            raise ValueError("No messages in active chat")
        return self._active_messages[-1].copy()

    def set_active_chat_history(self, messages: List[Dict[str, Any]]):
        """Sets history of an active chat."""
        if not self.active_path:
            raise ValueError("No active chat selected")

        node_id = self._get_node_id(self.active_path)

        with sqlite3.connect(self.db.db_path) as conn:
            # Delete existing messages
            conn.execute("DELETE FROM messages WHERE node_id = ?", (node_id,))

            # Insert new messages
            for i, msg in enumerate(messages):
                conn.execute(
                    """
                    INSERT INTO messages (node_id, role, content, image_path, position)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (node_id, msg["role"], msg["content"], msg.get("image_path"), i),
                )

        # Update cache
        self._active_messages = messages.copy()

    def clear_all_messages(self):
        """Clear all messages for the active chat."""
        if not self.active_path:
            raise ValueError("No active chat selected")

        node_id = self._get_node_id(self.active_path)

        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE node_id = ?", (node_id,))

        self._active_messages = []

    def clear_last_n_messages(self, n: int):
        """Clear the last `n` messages for the active chat."""
        if not self.active_path:
            raise ValueError("No active chat selected")

        n = max(0, min(n, len(self._active_messages)))
        if n == 0:
            return

        node_id = self._get_node_id(self.active_path)
        start_position = len(self._active_messages) - n

        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute(
                """
                DELETE FROM messages 
                WHERE node_id = ? AND position >= ?
                """,
                (node_id, start_position),
            )

        self._active_messages = self._active_messages[:-n]

    # def clear_messages_in_range(self, start: int, end: int):
    #     """Clear messages in the [start, end] range for the active chat."""
    #     if not self.active_path:
    #         raise ValueError("No active chat selected")

    #     total_messages = len(self._active_messages)
    #     start = max(0, start)
    #     end = min(total_messages - 1, end)

    #     if start > end:
    #         return

    #     node_id = self._get_node_id(self.active_path)

    #     with sqlite3.connect(self.db.db_path) as conn:
    #         # Delete messages in range
    #         conn.execute(
    #             """
    #             DELETE FROM messages
    #             WHERE node_id = ? AND position BETWEEN ? AND ?
    #             """,
    #             (node_id, start, end),
    #         )

    #         # Update positions for remaining messages
    #         conn.execute(
    #             """
    #             UPDATE messages
    #             SET position = position - ?
    #             WHERE node_id = ? AND position > ?
    #             """,
    #             (end - start + 1, node_id, end),
    #         )

    #     # Update cache
    #     self._active_messages = (
    #         self._active_messages[:start] + self._active_messages[end + 1 :]
    #     )

    def clear_messages_by_role(self, role: str):
        """Clear all messages for a given role in the active chat."""
        if not self.active_path:
            raise ValueError("No active chat selected")

        node_id = self._get_node_id(self.active_path)

        with sqlite3.connect(self.db.db_path) as conn:
            # Get positions of messages to delete
            positions = [
                row[0]
                for row in conn.execute(
                    """
                    SELECT position 
                    FROM messages 
                    WHERE node_id = ? AND role = ?
                    ORDER BY position
                    """,
                    (node_id, role),
                )
            ]

            if not positions:
                return

            # Delete messages with specified role
            conn.execute(
                """
                DELETE FROM messages 
                WHERE node_id = ? AND role = ?
                """,
                (node_id, role),
            )

            # Update positions for remaining messages
            for i, pos in enumerate(positions):
                conn.execute(
                    """
                    UPDATE messages 
                    SET position = position - 1
                    WHERE node_id = ? AND position > ?
                    """,
                    (node_id, pos - i),
                )

        # Update cache
        self._active_messages = [
            msg for msg in self._active_messages if msg["role"] != role
        ]

    def ensure_default_chat(self):
        """Ensure at least one default chat exists."""
        with sqlite3.connect(self.db.db_path) as conn:
            # Check if any chats exist
            has_chats = conn.execute(
                "SELECT 1 FROM nodes WHERE type = 'chat' LIMIT 1"
            ).fetchone()

            if not has_chats:
                default_chat_path = self.create_chat("💬 Default Chat")
                self.set_active_chat(default_chat_path)

    def print_node_hierarchy(self):
        """Debug method to print the entire node hierarchy."""
        with sqlite3.connect(self.db.db_path) as conn:

            def print_node(node_id, level=0):
                nodes = conn.execute(
                    """
                    SELECT id, name, type, parent_id 
                    FROM nodes 
                    WHERE parent_id = ? 
                    ORDER BY position
                """,
                    (node_id,),
                ).fetchall()

                for node in nodes:
                    print("  " * level + f"- {node[1]} ({node[2]})")
                    print_node(node[0], level + 1)

            root_id = conn.execute(
                "SELECT id FROM nodes WHERE parent_id IS NULL"
            ).fetchone()[0]

            print("Node Hierarchy:")
            print_node(root_id)

    # IMPORT/EXPORT from json

    def save_chats(self, filepath: str):
        """Save chat history from SQLite to a JSON file."""
        from pathlib import Path

        def get_node_path(node_id: int) -> str:
            """Get full path for a node."""
            with sqlite3.connect(self.db.db_path) as conn:
                path_components = []
                current_id = node_id

                while True:
                    result = conn.execute(
                        "SELECT name, parent_id FROM nodes WHERE id = ?", (current_id,)
                    ).fetchone()

                    if not result:
                        break

                    name, parent_id = result
                    if parent_id is None:  # Root node
                        break

                    path_components.append(name)
                    current_id = parent_id

                return "/" + "/".join(
                    reversed(path_components[:-1])
                )  # Exclude chat name

        def get_chat_data() -> dict:
            """Get all chats with their data."""
            with sqlite3.connect(self.db.db_path) as conn:
                # Get all chat nodes
                chats = conn.execute(
                    """
                    SELECT id, name, settings 
                    FROM nodes 
                    WHERE type = 'chat'
                    ORDER BY id
                    """
                ).fetchall()

                result = {}
                for chat_id, chat_name, settings_json in chats:
                    # Get messages for this chat
                    messages = conn.execute(
                        """
                        SELECT role, content, image_path 
                        FROM messages 
                        WHERE node_id = ? 
                        ORDER BY position
                        """,
                        (chat_id,),
                    ).fetchall()

                    # Convert messages to dict format
                    messages_data = []
                    for role, content, image_path in messages:
                        msg = {"role": role, "content": content}
                        if image_path:
                            msg["image_path"] = image_path
                        messages_data.append(msg)

                    # Build chat data
                    chat_data = {
                        "messages": messages_data,
                        "group": get_node_path(chat_id),
                    }

                    # Add settings if present
                    if settings_json:
                        chat_data["settings"] = json.loads(settings_json)

                    result[chat_name] = chat_data

                return result

        try:
            # Create directory if it doesn't exist
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Build save data
            save_data = {"chats": get_chat_data(), "active_path": self.active_path}

            # Save to file with pretty printing
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

        except IOError as e:
            raise IOError(f"Failed to save chat history: {str(e)}")

    def load_chats(self, file_path: str):
        """Import chat data from JSON file into SQLite database."""
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        chat_data = data.get("chats", {})
        active_path = data.get("active_path")

        with sqlite3.connect(self.db.db_path) as conn:
            # Start with clean slate - remove all existing nodes except root
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM nodes WHERE parent_id IS NOT NULL")

            # Get root node id
            root_id = conn.execute(
                "SELECT id FROM nodes WHERE parent_id IS NULL"
            ).fetchone()[0]

            # Helper function to ensure group exists and get its id
            def ensure_group_path(path_components):
                current_id = root_id
                current_path = []

                for group_name in path_components:
                    if not group_name:  # Skip empty components
                        continue

                    current_path.append(group_name)

                    # Check if group exists
                    result = conn.execute(
                        """
                        SELECT id FROM nodes 
                        WHERE parent_id = ? AND name = ?
                        """,
                        (current_id, group_name),
                    ).fetchone()

                    if result:
                        current_id = result[0]
                    else:
                        # Create new group
                        position = conn.execute(
                            "SELECT COUNT(*) FROM nodes WHERE parent_id = ?",
                            (current_id,),
                        ).fetchone()[0]

                        cursor = conn.execute(
                            """
                            INSERT INTO nodes (name, type, parent_id, position)
                            VALUES (?, ?, ?, ?)
                            """,
                            (group_name, "group", current_id, position),
                        )
                        current_id = cursor.lastrowid

                return current_id

            # Import chats
            for chat_name, chat_data in chat_data.items():
                # Process group path
                group_path = chat_data.get("group", "/").split("/")
                group_path = [p for p in group_path if p]  # Remove empty components
                parent_id = ensure_group_path(group_path)

                # Create chat node
                position = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE parent_id = ?", (parent_id,)
                ).fetchone()[0]

                cursor = conn.execute(
                    """
                    INSERT INTO nodes (name, type, parent_id, position, settings)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chat_name,
                        "chat",
                        parent_id,
                        position,
                        json.dumps(chat_data.get("settings", {})),
                    ),
                )
                chat_id = cursor.lastrowid

                # Import messages
                for i, msg in enumerate(chat_data.get("messages", [])):
                    conn.execute(
                        """
                        INSERT INTO messages (node_id, role, content, image_path, position)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            chat_id,
                            msg["role"],
                            msg["content"],
                            msg.get("image_path"),
                            i,
                        ),
                    )

        # Restore active chat if valid
        if active_path:
            try:
                self.set_active_chat(active_path)
            except ValueError:
                self.ensure_default_chat()
        else:
            self.ensure_default_chat()
