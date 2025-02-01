import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Callable, Dict
from ..tools import ensure_icon, get_button_config, get_list_style


class ChatTree:
    def __init__(self, parent_frame, chat_history, on_chat_select: Callable):
        self.chat_history = chat_history
        self.on_chat_select = on_chat_select
        self.previous_chat = None

        self.frame = tk.Frame(parent_frame)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Create middle frame for tree and scrollbar
        self.tree_frame = tk.Frame(self.frame)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure tree frame grid
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_frame.grid_rowconfigure(0, weight=1)

        # Create Treeview and scrollbar
        self.tree = ttk.Treeview(self.tree_frame, selectmode="browse")
        self.scrollbar = tk.Scrollbar(
            self.tree_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        # Position tree and scrollbar
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Configure columns
        self.tree.heading("#0", text="Chats", anchor=tk.W)

        # Add buttons
        self.button_frame = tk.Frame(self.frame)
        self.button_frame.pack(padx=10, pady=5, fill=tk.X)

        self.new_chat_button = tk.Button(
            self.button_frame,
            text="New Chat",
            command=self.new_chat,
            font=("Arial", 12),
        )
        self.new_chat_button.pack(padx=10, pady=5, fill=tk.X)

        self.new_group_button = tk.Button(
            self.button_frame,
            text="New Group",
            command=self.new_group,
            font=("Arial", 12),
        )
        self.new_group_button.pack(padx=10, pady=5, fill=tk.X)

        self.rename_button = tk.Button(
            self.button_frame,
            text="Rename",
            command=self.rename_selected,
            font=("Arial", 12),
        )
        self.rename_button.pack(padx=10, pady=5, fill=tk.X)

        self.delete_button = tk.Button(
            self.button_frame,
            text="Delete",
            command=self.delete_selected,
            font=("Arial", 12),
        )
        self.delete_button.pack(padx=10, pady=5, fill=tk.X)

        # Bind events
        self.tree.bind("<Button-1>", self.on_click)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Setup drag and drop
        self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.tree.bind("<B1-Motion>", self.on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_drag_release)
        self._drag_data = {"item": None, "x": 0, "y": 0}

        self.enabled = True
        self.load_tree()
        self.expand_to_path(self.chat_history.active_path)

    def get_item_path(self, item_id):
        """Get full path for a tree item"""
        path = []
        while item_id:
            name = self.tree.item(item_id)["text"]
            path.insert(0, name)
            item_id = self.tree.parent(item_id)
        return path

    def new_group(self):
        """Create a new group"""
        selection = self.tree.selection()
        parent_path = []

        if selection:
            item = selection[0]
            if "group" in self.tree.item(item)["tags"]:
                parent_path = self.get_item_path(item)
            else:
                parent = self.tree.parent(item)
                if parent:  # Check if parent exists
                    parent_path = self.get_item_path(parent)
                # If no parent, parent_path remains empty for root level

        group_name = simpledialog.askstring("New Group", "Enter group name:")
        if not group_name:
            return None

        group_name = ensure_icon(name=group_name, default_icon="📁")

        try:
            path = self.chat_history.create_group(group_name, parent_path)
            parent = self.get_tree_parent(
                parent_path
            )  # Will now correctly return '' for root level
            new_group = self.tree.insert(
                parent, "end", text=group_name, tags=("group",)
            )
            return new_group
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return None

    def new_chat(self):
        """Create a new chat"""
        selection = self.tree.selection()
        parent_path = []

        if selection:
            item = selection[0]
            if "group" in self.tree.item(item)["tags"]:
                parent_path = self.get_item_path(item)
            else:
                parent_path = self.get_item_path(self.tree.parent(item))

        chat_name = simpledialog.askstring("New Chat", "Enter chat name:")
        if not chat_name:
            return

        chat_name = ensure_icon(name=chat_name, default_icon="💬")

        try:
            path = self.chat_history.create_chat(chat_name, parent_path)
            parent = self.get_tree_parent(parent_path)
            chat_id = self.tree.insert(parent, "end", text=chat_name, tags=("chat",))
            self.tree.selection_set(chat_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def get_tree_parent(self, path):
        """Get tree item ID for parent path"""
        if not path:
            return ""  # Empty string explicitly represents root level

        current = ""
        for name in path:
            found = False
            for child in self.tree.get_children(current):
                if self.tree.item(child)["text"] == name:
                    current = child
                    found = True
                    break
            if not found:
                return ""  # Return root if path not found
        return current

    def rename_selected(self):
        """Rename selected item"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Rename", "Please select an item to rename")
            return

        item = selection[0]
        old_name = self.tree.item(item)["text"]
        path = self.get_item_path(item)

        new_name = simpledialog.askstring(
            "Rename", f"Rename '{old_name}' to:", initialvalue=old_name
        )

        if not new_name or new_name == old_name:
            return

        try:
            self.chat_history.rename_node(path, new_name)
            self.tree.item(item, text=new_name)
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def delete_selected(self):
        """Delete selected item"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Delete", "Please select an item to delete")
            return

        item = selection[0]
        name = self.tree.item(item)["text"]
        is_group = "group" in self.tree.item(item)["tags"]
        path = self.get_item_path(item)

        msg = f"Are you sure you want to delete {('group' if is_group else 'chat')} '{name}'?"
        if is_group:
            msg += "\nThis will delete all contents!"

        if not messagebox.askyesno("Confirm Delete", msg):
            return

        try:
            self.chat_history.delete_node(path)
            self.tree.delete(item)
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def on_click(self, event):
        """Handle single click"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "nothing":
            # Click outside any item - clear selection
            self.tree.selection_set()  # Clear selection
            return "break"  # Prevent default handling

    def on_select(self, event):
        """Handle tree item selection"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        if "chat" not in self.tree.item(item)["tags"]:
            return

        path = self.get_item_path(item)
        try:
            self.chat_history.set_active_chat(path)
            self.on_chat_select()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def switch_chats(self, event=None):
        """Switches chats"""
        if self.previous_chat != self.chat_history.active_path:
            previous_chat = self.previous_chat
            self.previous_chat = self.chat_history.active_path
            if previous_chat != None:
                self.expand_to_path(previous_chat)
                return "break"
        return None

    def on_double_click(self, event):
        """Handles double click."""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        if "group" in item.get("tags", []):
            return

        self.rename_selected()

    def on_drag_start(self, event):
        """Begin drag operation"""
        item = self.tree.identify_row(event.y)
        if item:
            self._drag_data["item"] = item
            self._drag_data["x"] = event.x
            self._drag_data["y"] = event.y

    def on_drag_motion(self, event):
        """Handle drag motion"""
        pass

    def on_drag_release(self, event):
        """End drag operation"""
        if not self._drag_data["item"]:
            return

        region = self.tree.identify_region(event.x, event.y)
        target = self.tree.identify_row(event.y)

        source_item = self._drag_data["item"]
        source_path = self.get_item_path(source_item)

        # Don't allow drop on self or descendants
        if target:
            current = target
            while current:
                if current == source_item:
                    self._drag_data["item"] = None
                    return
                current = self.tree.parent(current)

        try:
            if region == "nothing" or not target:
                # Move to root
                self.chat_history.move_node(source_path, [])
                self.tree.move(source_item, "", "end")

            else:
                target_path = self.get_item_path(target)
                target_tags = self.tree.item(target)["tags"]

                # Get target parent and position
                if "group" not in target_tags:
                    target_parent = self.tree.parent(target)
                    target_parent_path = (
                        self.get_item_path(target_parent) if target_parent else []
                    )

                    # Calculate position within parent
                    siblings = self.tree.get_children(target_parent)
                    position = siblings.index(target)

                else:
                    target_parent = target
                    target_parent_path = target_path
                    position = 0  # Insert at beginning of group

                # Move in history
                self.chat_history.move_node(source_path, target_parent_path, position)

                # Move in tree
                target_parent_id = target_parent if target_parent else ""
                self.tree.move(source_item, target_parent_id, position)

            self.tree.selection_set(source_item)

        except ValueError as e:
            messagebox.showerror("Error", str(e))

        finally:
            self._drag_data["item"] = None
            self._drag_data["x"] = 0
            self._drag_data["y"] = 0

    def load_tree(self):
        """Load the tree structure from history manager"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        def add_nodes(parent_path="", tree_parent=""):
            nodes = self.chat_history.get_nodes(parent_path)
            for node in nodes:
                name = node["name"]
                is_group = node["type"] == "group"

                # Insert node into tree
                item_id = self.tree.insert(
                    tree_parent,
                    "end",
                    text=name,
                    tags=("group" if is_group else "chat",),
                )

                # Recursively add children for groups
                if is_group:
                    new_path = parent_path + [name] if parent_path else [name]
                    add_nodes(new_path, item_id)

        # Start recursive loading from root
        add_nodes()

    def enable(self):
        """Enable chat tree input."""
        self.enabled = True
        self.set_tree_state(enabled=True)
        self.new_chat_button.config(state=tk.NORMAL)
        self.new_group_button.config(state=tk.NORMAL)
        self.rename_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.NORMAL)

    def disable(self):
        """Disable chat tree input."""
        self.enabled = False
        self.set_tree_state(enabled=False)
        self.new_chat_button.config(state=tk.DISABLED)
        self.new_group_button.config(state=tk.DISABLED)
        self.rename_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)

    def set_tree_state(self, enabled: bool):
        """Enable or disable the tree"""
        self.tree.configure(takefocus=enabled)
        self.tree.bind("<Button-1>", lambda e: "break" if not enabled else None)
        self.tree.bind(
            "<ButtonPress-1>",
            lambda e: "break" if not enabled else self.on_drag_start(e),
        )
        self.tree.bind(
            "<B1-Motion>", lambda e: "break" if not enabled else self.on_drag_motion(e)
        )
        self.tree.bind(
            "<ButtonRelease-1>",
            lambda e: "break" if not enabled else self.on_drag_release(e),
        )
        self.tree.bind(
            "<Double-1>", lambda e: "break" if not enabled else self.on_double_click(e)
        )

    def expand_to_path(self, path):
        """Expand tree to show given path and select the last item"""
        if not path:
            return

        # Find and expand each parent in path
        current = ""
        for name in path:
            found = False
            for child in self.tree.get_children(current):
                if self.tree.item(child)["text"] == name:
                    current = child
                    self.tree.see(current)
                    self.tree.selection_set(current)
                    found = True
                    break
            if not found:
                break

    def apply_theme(self, theme):

        style = get_list_style(theme=theme)
        self.frame.configure(bg=theme["bg"], borderwidth=1, relief="solid")
        self.tree_frame.configure(bg=theme["bg"], borderwidth=1, relief="solid")
        self.tree.configure(style="Treeview")

        # Configure scrollbar
        self.scrollbar.configure(
            bg=theme["scrollbar_bg"],
            activebackground=theme["scrollbar_hover"],
            troughcolor=theme["scrollbar_bg"],
            width=12,
        )

        self.button_frame.configure(bg=theme["bg"], borderwidth=1, relief="solid")

        button_config = get_button_config(theme)
        for button in [
            self.new_chat_button,
            self.new_group_button,
            self.rename_button,
            self.delete_button,
        ]:
            button.configure(**button_config)
