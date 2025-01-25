import json
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict


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

    def __init__(self, markdown_enabled=False, replies_allowed=True, llm=LLMSettings()):
        self.markdown_enabled = markdown_enabled
        self.replies_allowed = replies_allowed
        self.llm: LLMSettings = llm
        # self._custom_settings: Dict[str, Any] = {}

    def to_dict(self) -> dict:
        """Convert settings to dictionary for serialization, excluding default values."""
        result = {}

        # Only include non-default values
        if self.markdown_enabled:
            result["markdown_enabled"] = True
        if not self.replies_allowed:
            result["replies_allowed"] = False

        # Include LLM settings only if they differ from defaults
        llm_dict = self.llm.to_dict()
        if llm_dict:
            result["llm"] = llm_dict

        # Include custom settings only if not empty
        # if self._custom_settings:
        #   result["custom_settings"] = self._custom_settings

        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ChatSettings":
        """Create settings from dictionary."""
        settings = cls()
        settings.markdown_enabled = data.get("markdown_enabled", False)
        settings.replies_allowed = data.get("replies_allowed", True)
        settings.llm = LLMSettings.from_dict(data.get("llm"))
        # settings._custom_settings = data.get("custom_settings", {})
        return settings

    # def set_custom_setting(self, key: str, value: Any) -> None:
    #     """Set a custom setting value."""
    #     if value is None:
    #         self._custom_settings.pop(key, None)
    #     else:
    #         self._custom_settings[key] = value

    # def get_custom_setting(self, key: str, default: Any = None) -> Any:
    #     """Get a custom setting value."""
    #     return self._custom_settings.get(key, default)

    def replace(self, **kwargs):
        # Create a new object with the specified updated attributes
        return ChatSettings(**{**self.__dict__, **kwargs})


class ChatHistory:
    """Manages chat history."""

    def __init__(
        self, default_prompt: Optional[str], history_path=None, history_sort=False
    ):
        self.root = {
            "type": "group",
            "name": "/",
            "children": {},  # {name: {type: group/chat, children/messages}}
        }
        self.active_path = None  # List of names forming path to active chat
        self.default_prompt = default_prompt

        self.history_sort = history_sort
        if history_path:
            self.load_chats(history_path)

        self.ensure_default_chat()

    def ensure_default_chat(self):
        """Ensure at least one default chat exists."""
        if not self.root["children"]:
            default_chat_path = self.create_chat("💬 Default Chat")
            self.set_active_chat(default_chat_path)

    def _get_node_by_path(self, path):
        """Get node at specified path"""
        current = self.root
        if not path:
            return current

        for name in path:
            if name not in current["children"]:
                raise ValueError(f"Path not found: {'/'.join(path)}")
            current = current["children"][name]
        return current

    def _get_parent_path(self, path):
        """Get parent path and name from full path"""
        return path[:-1], path[-1] if path else None

    def create_group(self, name, parent_path=None):
        """Create a new group at specified path"""
        parent = self._get_node_by_path(parent_path if parent_path else [])

        if name in parent["children"]:
            raise ValueError(
                f"Item already exists at path: {'/'.join(parent_path or [])}/{name}"
            )

        parent["children"][name] = {"type": "group", "name": name, "children": {}}

        return (parent_path or []) + [name]

    def create_chat(self, name, parent_path=None):
        """Create a new chat at specified path"""
        parent = self._get_node_by_path(parent_path if parent_path else [])

        if name in parent["children"]:
            raise ValueError(
                f"Item already exists at path: {'/'.join(parent_path or [])}/{name}"
            )

        settings = ChatSettings()
        settings.llm.system_prompt = self.default_prompt

        parent["children"][name] = {
            "type": "chat",
            "name": name,
            "settings": settings.to_dict(),
            "messages": [{"role": "tool", "content": "Welcome to your new chat!"}],
        }

        return (parent_path or []) + [name]

    def rename_node(self, old_path, new_name):
        """Rename group or chat at specified path"""
        parent_path, old_name = self._get_parent_path(old_path)
        parent = self._get_node_by_path(parent_path)

        if new_name in parent["children"]:
            raise ValueError(f"Item {new_name} already exists in this location")

        # Move node to new name
        node = parent["children"].pop(old_name)
        node["name"] = new_name
        parent["children"][new_name] = node

        # Update active path if needed
        if self.active_path and old_path == self.active_path[: len(old_path)]:
            self.active_path = (
                parent_path + [new_name] + self.active_path[len(old_path) :]
            )

    def delete_node(self, path):
        """Delete group or chat at specified path"""
        parent_path, name = self._get_parent_path(path)
        parent = self._get_node_by_path(parent_path)

        # Reset active path if deleting active chat or its parent
        if self.active_path and path == self.active_path[: len(path)]:
            self.active_path = None

        del parent["children"][name]

    def move_node(self, source_path, target_path, position=None):
        """Move a node to a new location with optional position.

        Args:
            source_path: Path of node to move
            target_path: Destination path
            position: Optional index position within target group
        """
        source_parent_path, source_name = self._get_parent_path(source_path)
        source_parent = self._get_node_by_path(source_parent_path)
        target_parent = self._get_node_by_path(target_path)

        # Moving within same parent - reorder children
        if source_parent is target_parent:
            if position is not None:
                # Get ordered list of children
                children = list(source_parent["children"].items())

                # Find source item
                source_idx = next(
                    i for i, (name, _) in enumerate(children) if name == source_name
                )

                # Remove and reinsert at new position
                item = children.pop(source_idx)
                children.insert(position, item)

                # Update parent's children dict with new order
                source_parent["children"] = dict(children)
                return

        # Regular move between different parents
        if source_name in target_parent["children"]:
            raise ValueError(f"Item {source_name} already exists in target location")

        node = source_parent["children"].pop(source_name)
        target_parent["children"][source_name] = node

        # Update active path if needed
        if self.active_path and source_path == self.active_path[: len(source_path)]:
            self.active_path = (
                target_path + [source_name] + self.active_path[len(source_path) :]
            )

    def get_chat_settings(self, path=None) -> ChatSettings:
        """Get settings for specified chat."""
        if path is None:
            path = self.active_path

        node = self._get_node_by_path(path)
        if node["type"] != "chat":
            raise ValueError("Not a chat node")

        # Create settings if they don't exist (backward compatibility)
        if "settings" not in node:
            node["settings"] = ChatSettings().to_dict()

        return ChatSettings.from_dict(node["settings"])

    def set_chat_settings(self, settings: ChatSettings, path=None) -> None:
        """Set settings for specified chat."""
        if path is None:
            path = self.active_path

        node = self._get_node_by_path(path)
        if node["type"] != "chat":
            raise ValueError("Not a chat node")

        node["settings"] = settings.to_dict()

    def get_chat_messages(self, path=None):
        """Get messages for chat at specified path"""
        if path is None:
            path = self.active_path

        node = self._get_node_by_path(path)
        if node["type"] != "chat":
            raise ValueError("Not a chat node")
        return node["messages"]

    def get_nodes(self, path=None):
        """Get all nodes at the specified path."""
        # Get parent node
        parent = self._get_node_by_path(path if path else [])

        # Convert children to list format expected by tree
        nodes = []
        for name, node in parent["children"].items():
            nodes.append({"name": name, "type": node["type"]})

        # Sort nodes: groups first, then alphabetically
        if self.history_sort:
            return sorted(
                nodes, key=lambda x: (x["type"] != "group", x["name"].lower())
            )

        return nodes

    def append_message(self, role, content, image_path=None):
        """Append message to active chat"""
        node = self._ensure_active_chat_node()
        message = {"role": role, "content": content}
        if image_path:
            message["image_path"] = image_path
        node["messages"].append(message)

    def append_message_partial(self, role, token, is_first_token):
        """Append message token to active chat"""
        if is_first_token:
            self.append_message(role, "")

        # Update the content of the last message
        messages = self.get_active_chat_messages()
        if messages and messages[-1]["role"] == role:
            current_content = messages[-1]["content"]
            messages[-1]["content"] = current_content + token

    def get_last_message(self):
        """Returns last message in the active chat."""
        return self.get_chat_messages(self.active_path)[-1]

    def update_last_message(self, role, token):
        """Update last message in active chat"""
        if not self.active_path:
            raise ValueError("No active chat")
        node = self._get_node_by_path(self.active_path)

        if node and node["messages"][-1]["role"] == role:
            node["messages"][-1]["content"] += token

    def set_active_chat(self, path):
        """Set active chat by path"""
        node = self._get_node_by_path(path)
        if node["type"] != "chat":
            raise ValueError("Selected path is not a chat")
        self.active_path = path

    def get_active_chat_messages(self):
        """Get messages from active chat"""
        if not self.active_path:
            return []
        return self.get_chat_messages(self.active_path)

    def load_chats(self, file_path):
        """Load chat data from external source"""

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        self.root["children"] = {}

        chat_data = data.get("chats", {})
        self.active_path = data.get("active_path")

        for chat_name, chat_data in chat_data.items():
            # Split group path into components
            group_path = chat_data.get("group", "/").split("/")
            group_path = [p for p in group_path if p]  # Remove empty components

            # Create group hierarchy
            current_path = []
            for group_name in group_path:
                try:
                    self.create_group(group_name, current_path)
                except ValueError:
                    pass  # Group already exists
                current_path.append(group_name)

            # Create chat in final group
            try:
                chat_path = self.create_chat(chat_name, current_path)
                node = self._get_node_by_path(chat_path)
                if "settings" in chat_data:
                    node["settings"] = chat_data["settings"]
                node["messages"] = chat_data["messages"]
            except ValueError:
                continue  # Skip if chat already exists

        # Restore active chat if valid
        if self.active_path and self._get_node_by_path(self.active_path):
            self.set_active_chat(self.active_path)
        else:
            self.ensure_default_chat()

    def save_chats(self, filepath):
        """Save chat history to a JSON file."""
        import json
        from pathlib import Path

        def process_node(node, current_path):
            """Convert node to saveable format"""
            result = {}

            if node["type"] == "chat":
                # For chat nodes, store messages and group path
                result[node["name"]] = {
                    "settings": node["settings"],
                    "messages": node["messages"],
                    "group": "/" + "/".join(current_path) if current_path else "/",
                }
            else:
                # For group nodes, process all children
                for child_name, child_node in node["children"].items():
                    child_result = process_node(
                        child_node,
                        (
                            current_path + [node["name"]]
                            if node["name"] != "/"
                            else current_path
                        ),
                    )
                    result.update(child_result)

            return result

        try:
            # Create directory if it doesn't exist
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Convert tree structure to flat format
            chat_data = process_node(self.root, [])

            # Include active path in saved data
            save_data = {
                "chats": chat_data,
                "active_path": self.active_path,
            }

            # Save to file with pretty printing
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

        except IOError as e:
            raise IOError(f"Failed to save chat history: {str(e)}")

    def set_active_chat_history(self, messages):
        """Sets history of an active chat."""
        node = self._get_node_by_path(self.active_path)
        node["messages"] = messages

    def clear_all_messages(self):
        """Clear all messages for the active chat."""
        node = self._ensure_active_chat_node()

        node["messages"] = []

    def clear_last_n_messages(self, n: int):
        """Clear the last `n` messages for the active chat."""
        node = self._ensure_active_chat_node()

        total_messages = len(node["messages"])

        # Clamp `n` to a valid range
        n = max(0, min(n, total_messages))

        if n > 0:
            node["messages"] = node["messages"][:-n]

    def clear_messages_in_range(self, start: int, end: int):
        """Clear messages in the [start, end] range for the active chat."""
        node = self._ensure_active_chat_node()

        total_messages = len(node["messages"])

        # Clamp start and end to valid indices
        start = max(0, start)
        end = min(total_messages - 1, end)

        if start <= end:
            node["messages"] = node["messages"][:start] + node["messages"][end + 1 :]

    def clear_messages_by_role(self, role: str):
        """Clear all messages for a given role in the active chat."""
        node = self._ensure_active_chat_node()

        node["messages"] = [msg for msg in node["messages"] if msg["role"] != role]

    def _ensure_active_chat_node(self):
        if not self.active_path:
            raise ValueError("No active chat selected.")

        node = self._get_node_by_path(self.active_path)
        if node["type"] != "chat":
            raise ValueError("Active path is not a chat.")

        return node
