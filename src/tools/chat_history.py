from typing import Callable


class ChatHistory:
    """Manages chat history."""

    def __init__(self):
        self.root = {
            "type": "group",
            "name": "/",
            "children": {},  # {name: {type: group/chat, children/messages}}
        }
        self.active_path = None  # List of names forming path to active chat

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

        parent["children"][name] = {
            "type": "chat",
            "name": name,
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

    def move_node(self, source_path, target_path):
        """Move a node to a new location"""
        source_parent_path, source_name = self._get_parent_path(source_path)
        source_parent = self._get_node_by_path(source_parent_path)
        target_parent = self._get_node_by_path(target_path)

        if source_name in target_parent["children"]:
            raise ValueError(f"Item {source_name} already exists in target location")

        # Move the node
        node = source_parent["children"].pop(source_name)
        target_parent["children"][source_name] = node

        # Update active path if needed
        if self.active_path and source_path == self.active_path[: len(source_path)]:
            self.active_path = (
                target_path + [source_name] + self.active_path[len(source_path) :]
            )

    def get_chat_messages(self, path):
        """Get messages for chat at specified path"""
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
        return sorted(nodes, key=lambda x: (x["type"] != "group", x["name"].lower()))

    def append_message(self, role, content):
        """Append message to active chat"""
        if not self.active_path:
            raise ValueError("No active chat")

        node = self._get_node_by_path(self.active_path)
        if node["type"] != "chat":
            raise ValueError("Active path is not a chat")

        node["messages"].append({"role": role, "content": content})

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

    def load_chats(self, chat_data):
        """Load chat data from external source"""
        self.root["children"] = {}

        self.active_path = None  # Reset active chat/group

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
                node["messages"] = chat_data["messages"]
            except ValueError:
                continue  # Skip if chat already exists

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

            # Save to file with pretty printing
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)

        except IOError as e:
            raise IOError(f"Failed to save chat history: {str(e)}")

    def set_active_chat_history(self, messages):
        """Sets history of an active chat."""
        node = self._get_node_by_path(self.active_path)
        node["messages"] = messages
