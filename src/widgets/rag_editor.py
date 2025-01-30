import tkinter as tk
import os
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Optional
from ..models import RAG
from ..tools import get_button_config, get_list_style


class RAGManagementUI:
    def __init__(self, parent, rag_model: RAG, on_chat_start: Callable):
        """Initialize the RAG Management UI.

        Args:
            parent: The parent tkinter widget
            rag_model: Instance of RAG class
            on_chat_start: Callback function when starting a new chat
        """
        self.parent = parent
        self.rag_model = rag_model
        self.on_chat_start = on_chat_start

        self.rag_visible = True
        self.current_collection: Optional[str] = None

        self.frame = tk.Frame(parent)
        self.frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Collection Management Section
        self.collection_frame = tk.LabelFrame(self.frame, text="Collection Management")
        self.collection_frame.pack(fill=tk.X, padx=10, pady=5)

        # Collection management buttons
        self.new_collection_button = tk.Button(
            self.collection_frame,
            text="New",
            command=self.create_new_collection,
        )
        self.new_collection_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.rename_collection_button = tk.Button(
            self.collection_frame,
            text="Rename",
            command=self.rename_collection,
        )
        self.rename_collection_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.delete_button = tk.Button(
            self.collection_frame, text="Delete Selected", command=self.delete_selected
        )
        self.delete_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Data Store Section
        self.data_store_frame = tk.LabelFrame(self.frame, text="Data Store")
        self.data_store_frame.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)

        # Create a frame to hold the Treeview and scrollbars
        self.tree_frame = tk.Frame(self.data_store_frame)
        self.tree_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

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
        self.data_store_tree.heading("Type", text="File Type")

        # Set column widths
        self.data_store_tree.column("Name", width=400, minwidth=200)
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

        self.upload_button = tk.Button(
            self.data_store_frame, text="Upload File", command=self.upload_file
        )
        self.upload_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.context_button = tk.Button(
            self.data_store_frame, text="Set Query", command=self.set_query
        )
        self.context_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Initialize the UI
        self.refresh_data_store()

    def on_tree_select(self, event):
        """Handle tree selection changes."""
        selected_items = self.data_store_tree.selection()
        if not selected_items:
            return

        # Get the selected item and its parent (if any)
        item = selected_items[0]
        parent = self.data_store_tree.parent(item)

        # If the item is a collection (no parent)
        if not parent:
            self.current_collection = item.replace("collection_", "")
        else:
            # If the item is a document, use its parent collection
            self.current_collection = parent.replace("collection_", "")

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
                ("Comma-Separated Values", "*.csv"),
                ("Microsoft Word", "*.docx"),
                ("EPUB ebook format", "*.epub"),
                ("Text Files", "*.txt"),
                ("Markdown Files", "*.md"),
                ("PDF Files", "*.pdf"),
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
        """Delete selected items (files or collections)."""
        selected_items = self.data_store_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "No items selected.")
            return

        try:
            for item in selected_items:
                if item.startswith("collection_"):
                    # Delete entire collection
                    collection_name = item.replace("collection_", "")
                    if messagebox.askyesno(
                        "Confirm Delete",
                        f"Are you sure you want to delete the entire collection '{collection_name}'?",
                    ):
                        self.rag_model.delete_collection(collection_name)
                        if self.current_collection == collection_name:
                            self.current_collection = None
                else:
                    # Delete single document
                    source_path = self.data_store_tree.item(item)["tags"][0]
                    parent_id = self.data_store_tree.parent(item)
                    collection_name = parent_id.replace("collection_", "")
                    self.rag_model.delete_document(
                        collection_name=collection_name, source_path=source_path
                    )

            self.refresh_data_store()
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

    def ask_question(self):
        """Ask a question to the selected collection."""
        if not self.current_collection:
            messagebox.showwarning("Warning", "Please select a collection first.")
            return

        question = tk.simpledialog.askstring(
            "Ask Question",
            "Enter your question:",
        )

        if question:
            try:
                answer = self.rag_model.answer_question(
                    question=question,
                    collection_name=self.current_collection,
                )

                # Start chat with the answer
                self.on_chat_start(
                    [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ]
                )

            except Exception as e:
                messagebox.showerror("Error", f"Failed to get answer: {e}")

    def set_query(self):
        """Sets context to selected chat."""
        print("not implemented")

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
