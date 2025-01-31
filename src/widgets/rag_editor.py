import tkinter as tk
import os
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Optional, Set
from llama_index.core.vector_stores import (
    MetadataFilters,
    ExactMatchFilter,
    FilterCondition,
)
from ..models import RAG
from ..tools import get_button_config, get_list_style
from .toolbar import create_tooltip


class RAGManagementUI:
    def __init__(self, parent, rag_model: RAG, on_context_set: Callable):
        """Initialize the RAG Management UI.

        Args:
            parent: The parent tkinter widget
            rag_model: Instance of RAG class
            on_context_set: Callback function to set RAG context
        """
        self.parent = parent
        self.rag_model = rag_model
        self.on_context_set = on_context_set

        self.rag_visible = True
        self.current_collection: Optional[str] = None

        self.frame = tk.Frame(parent)
        self.frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Data Store Section
        self.data_store_frame = tk.LabelFrame(self.frame, text="Data Store")
        self.data_store_frame.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)

        # Create a frame to hold the Treeview and scrollbars
        self.tree_frame = tk.Frame(self.data_store_frame)
        self.tree_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        # Collection Management Section
        self.collection_frame = tk.LabelFrame(self.frame)
        self.collection_frame.pack(fill=tk.X, padx=10, pady=5)

        button_style = {
            "width": 2,
            "height": 1,
            "relief": "flat",
            "font": ("TkDefaultFont", 8),
        }

        # Collection management buttons
        self.new_collection_button = tk.Button(
            self.collection_frame,
            text="➕",
            command=self.create_new_collection,
            **button_style,
        )
        self.new_collection_button.pack(side=tk.LEFT, padx=5, pady=5)
        create_tooltip(self.new_collection_button, "Create New Collection")

        self.upload_button = tk.Button(
            self.collection_frame, text="📎", command=self.upload_file, **button_style
        )
        self.upload_button.pack(side=tk.LEFT, padx=5, pady=5)
        create_tooltip(self.upload_button, "Upload New Document")

        self.rename_collection_button = tk.Button(
            self.collection_frame,
            text="📝",
            command=self.rename_collection,
            **button_style,
        )
        self.rename_collection_button.pack(side=tk.LEFT, padx=5, pady=5)
        create_tooltip(self.rename_collection_button, "Rename Collection")

        self.delete_button = tk.Button(
            self.collection_frame,
            text="🗑",
            command=self.delete_selected,
            **button_style,
        )
        self.delete_button.pack(side=tk.LEFT, padx=5, pady=5)
        create_tooltip(self.delete_button, "Delete Selected Documents")

        self.context_button = tk.Button(
            self.collection_frame, text="📍", command=self.set_context, **button_style
        )
        self.context_button.pack(side=tk.RIGHT, padx=5, pady=5)
        create_tooltip(self.context_button, "Set Context")

        # Configure style for proper row height
        style = ttk.Style()
        style.configure(
            "RAG.Treeview",
            rowheight=36,
            font=("TkDefaultFont", 10),
        )

        # Modified Treeview structure
        self.data_store_tree = ttk.Treeview(
            self.tree_frame,
            columns=("Name", "Type"),
            show="tree headings",
            selectmode="extended",
            style="RAG.Treeview",
        )
        self.data_store_tree.heading("Name", text="File Name")
        self.data_store_tree.heading("Type", text="Type")

        # Set column widths
        self.data_store_tree.column("Name", width=300, minwidth=150)
        self.data_store_tree.column("Type", width=100, minwidth=80)

        # Create vertical scrollbar
        self.vsb = tk.Scrollbar(
            self.tree_frame, orient="vertical", command=self.data_store_tree.yview
        )
        self.data_store_tree.configure(yscrollcommand=self.vsb.set)

        # Grid layout for Treeview and scrollbars
        self.data_store_tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")

        # Configure grid weights
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        # Bind tree selection event
        self.data_store_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Initialize the UI
        self.refresh_data_store()

    def on_tree_select(self, event):
        """Handle tree selection changes."""
        selected_items = self.data_store_tree.selection()
        if not selected_items:
            return

        # Identify the collection
        first_item = selected_items[0]
        if first_item.startswith("collection_"):
            # If collection node selected, select all its documents
            collection_name = first_item.replace("collection_", "")
            self.current_collection = collection_name

            # Clear and select all documents in this collection
            self.data_store_tree.selection_remove(*self.data_store_tree.selection())
            for item in self.data_store_tree.get_children(first_item):
                self.data_store_tree.selection_add(item)
        else:
            # For document selection, ensure all are from same collection
            parent_collections = {
                self.data_store_tree.parent(item) for item in selected_items
            }
            if len(parent_collections) > 1:
                # If multiple collections, keep only first selection
                self.data_store_tree.selection_remove(*selected_items[1:])

            collection_parent = self.data_store_tree.parent(first_item)
            self.current_collection = collection_parent.replace("collection_", "")

        self.update_button_states()

    def update_button_states(self):
        """Update button states based on current selection."""
        has_collection = bool(self.current_collection)
        self.rename_collection_button.config(
            state="normal" if has_collection else "disabled"
        )
        self.upload_button.config(state="normal" if has_collection else "disabled")
        self.context_button.config(state="normal" if has_collection else "disabled")

    def create_new_collection(self):
        """Create a new collection."""
        name = tk.simpledialog.askstring("New Collection", "Enter collection name:")
        if name:
            try:
                _ = self.rag_model.get_collection(name)
                self.current_collection = name
                self.refresh_data_store()

                # Expand the newly created collection
                collection_id = f"collection_{name}"
                self.data_store_tree.see(collection_id)
                self.data_store_tree.selection_set(collection_id)
                self.data_store_tree.item(collection_id, open=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create collection: {e}")

    def upload_file(self):
        """Handle file uploads."""
        if not self.current_collection:
            messagebox.showwarning("Warning", "Please select a collection first.")
            return

        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Text Files", "*.txt"),
                ("Markdown Files", "*.md"),
                ("PDF Files", "*.pdf"),
                ("Comma-Separated Values", "*.csv"),
                ("Microsoft Word", "*.docx"),
                ("EPUB ebook format", "*.epub"),
            ]
        )
        if not file_path:
            return

        try:
            # Add document to the current collection
            self.rag_model.add_document(
                file_path=file_path, collection_name=self.current_collection
            )

            # Refresh the tree view
            self.refresh_data_store()

            # Expand the current collection and collapse others
            for item in self.data_store_tree.get_children():
                if item == f"collection_{self.current_collection}":
                    self.data_store_tree.item(item, open=True)
                else:
                    self.data_store_tree.item(item, open=False)

            # Select the newly added file
            collection_node = f"collection_{self.current_collection}"
            self.data_store_tree.see(collection_node)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload file: {e}")

    def refresh_data_store(self):
        """Refresh the data store display with hierarchical view."""
        # Store the currently expanded collections
        expanded_collections = {
            item
            for item in self.data_store_tree.get_children()
            if self.data_store_tree.item(item)["open"]
        }

        self.data_store_tree.delete(*self.data_store_tree.get_children())

        try:
            # Get all collections and their info
            collections = self.rag_model.list_collections()

            for collection_info in collections:
                collection_name = collection_info["name"]
                collection_id = f"collection_{collection_name}"

                # Add collection node
                self.data_store_tree.insert(
                    "", tk.END, iid=collection_id, text=collection_name, values=("", "")
                )

                # Add documents under collection
                for source in collection_info["unique_sources"]:
                    file_name = os.path.basename(source)
                    file_type = Path(source).suffix[1:].upper()
                    doc_id = f"doc_{collection_name}_{hash(source)}"

                    self.data_store_tree.insert(
                        collection_id,
                        tk.END,
                        iid=doc_id,
                        tags=(source,),
                        values=(file_name, file_type),
                    )

            # Restore expanded state
            for collection_id in expanded_collections:
                if self.data_store_tree.exists(collection_id):
                    self.data_store_tree.item(collection_id, open=True)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh data store: {e}")

        self.update_button_states()

    def delete_selected(self):
        """Delete selected documents and cleanup empty collections."""

        selected_items = self.data_store_tree.selection()
        selected_docs = [
            item for item in selected_items if not item.startswith("collection_")
        ]

        doc_count = len(selected_docs)
        if doc_count == 0:
            messagebox.showwarning("Warning", "No documents selected for deletion.")
            return

        # Confirm deletion
        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete {doc_count} document(s)?",
        ):
            return

        try:
            for item in selected_docs:
                source_path = self.data_store_tree.item(item)["tags"][0]
                parent_id = self.data_store_tree.parent(item)
                collection_name = parent_id.replace("collection_", "")

                self.rag_model.delete_document(
                    collection_name=collection_name, source_path=source_path
                )

            # Refresh data store to reflect deletions
            self.refresh_data_store()
            self.update_button_states()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete items: {e}")

    def rename_collection(self):
        """Rename the selected collection."""
        if not self.current_collection:
            messagebox.showwarning("Warning", "Please select a collection first.")
            return

        new_name = tk.simpledialog.askstring(
            "Rename Collection",
            "Enter new collection name:",
            initialvalue=self.current_collection,
        )

        if new_name and new_name != self.current_collection:
            try:
                self.rag_model.rename_collection(
                    old_name=self.current_collection, new_name=new_name
                )

                # Update current collection
                self.current_collection = new_name
                self.refresh_data_store()

                # Expand the renamed collection
                collection_id = f"collection_{new_name}"
                self.data_store_tree.see(collection_id)
                self.data_store_tree.selection_set(collection_id)
                self.data_store_tree.item(collection_id, open=True)

            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename collection: {e}")

    def set_context(self):
        """Sets context to selected chat."""
        if not self.current_collection:
            messagebox.showwarning("Warning", "Please select a collection first.")
            return

        selected_items = self.data_store_tree.selection()

        # Exclude collection nodes
        document_items = [
            item for item in selected_items if not item.startswith("collection_")
        ]

        if not document_items:
            return None

        selected_sources = {
            self.data_store_tree.item(item)["tags"][0] for item in document_items
        }

        metadata_filers = (
            MetadataFilters(
                filters=[
                    ExactMatchFilter(key="source", value=source)
                    for source in selected_sources
                ],
                condition=FilterCondition.OR,
            )
            if len(selected_sources) > 0
            else None
        )

        if not selected_sources:
            if not messagebox.askyesno(
                "No Documents Selected",
                "No documents are selected. Do you want to search across all documents in the collection?",
            ):
                return
            selected_sources = None

        self.on_context_set(
            self.current_collection,
            metadata_filters=metadata_filers,
        )

    def toggle(self):
        """Toggle the visibility of the RAG panel."""
        if not self.rag_model:
            return

        if self.rag_visible:
            self.frame.pack_forget()
        else:
            self.frame.pack(fill=tk.BOTH, expand=True)
        self.rag_visible = not self.rag_visible

    def apply_theme(self, theme):
        self.theme = theme

        self.frame.configure(bg=theme["bg"], borderwidth=1, relief="solid")
        self.collection_frame.configure(
            bg=theme["bg"], fg=theme["fg"], borderwidth=1, relief="solid"
        )
        self.data_store_frame.configure(
            bg=theme["bg"], fg=theme["fg"], borderwidth=1, relief="solid"
        )
        self.tree_frame.configure(bg=theme["bg"])

        # Configure buttons with common style
        button_config = {
            "bg": theme["button_bg"],
            "fg": theme["button_fg"],
            "activebackground": theme["button_bg_hover"],
            "activeforeground": theme["button_fg"],
            "font": ("Arial", 12),
            "relief": "solid",
            "borderwidth": 1,
        }

        button_config = get_button_config(theme)
        for button in [
            self.new_collection_button,
            self.rename_collection_button,
            self.upload_button,
            self.context_button,
            self.delete_button,
        ]:
            button.configure(**button_config)

        # Configure scrollbar
        self.vsb.configure(
            bg=theme["scrollbar_bg"],
            activebackground=theme["scrollbar_hover"],
            troughcolor=theme["scrollbar_bg"],
            width=12,
        )

        # Apply custom styles
        style = get_list_style(theme=theme)

        # Apply styles to Treeview
        self.data_store_tree.configure(style="Treeview")
