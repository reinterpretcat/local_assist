import tkinter as tk
import os
from tkinter import ttk, filedialog, messagebox
from typing import Optional
from ..models import RAG
from ..tools import get_button_config, get_list_style


class RAGManagementUI:
    def __init__(self, parent, rag: RAG, on_chat_start):
        """Initialize the RAG Management UI."""
        self.parent = parent
        self.rag_model = rag
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
                self.rag_model.get_or_create_collection(name)
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
            ]
        )
        if not file_path:
            return

        try:
            # Add document to the current collection
            self.rag_model.add_document(
                collection_name=self.current_collection, file_path=file_path
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
            # Get all collections and document references
            all_collections = self.rag_model.collections.keys()
            document_refs = self.rag_model.get_document_refs()
            collections_dict = {}

            # Group documents by collection and source file
            for doc_ref in document_refs.values():
                if doc_ref.collection_name not in collections_dict:
                    collections_dict[doc_ref.collection_name] = set()
                collections_dict[doc_ref.collection_name].add(doc_ref.source)

            # Add all collections, even if empty
            for collection_name in all_collections:
                collection_id = f"collection_{collection_name}"
                self.data_store_tree.insert(
                    "", tk.END, iid=collection_id, text=collection_name, values=("", "")
                )

                # Add documents under collection if they exist
                sources = collections_dict.get(collection_name, set())
                for source_path in sources:
                    file_name = os.path.basename(source_path)
                    file_type = os.path.splitext(source_path)[1][1:].upper()
                    doc_id = f"doc_{collection_name}_{hash(source_path)}"

                    self.data_store_tree.insert(
                        collection_id,
                        tk.END,
                        iid=doc_id,
                        tags=(source_path,),
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
                        self.rag_model.chroma_client.delete_collection(collection_name)
                        if self.current_collection == collection_name:
                            self.current_collection = None
                else:
                    # Delete single document
                    source_path = self.data_store_tree.item(item)["tags"][0]
                    parent_id = self.data_store_tree.parent(item)
                    collection_name = parent_id.replace("collection_", "")
                    collection = self.rag_model.get_or_create_collection(
                        collection_name
                    )
                    collection.collection.delete(where={"source": source_path})

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
                # Get the old collection
                old_collection = self.rag_model.get_or_create_collection(
                    self.current_collection
                )
                # Create new collection
                new_collection = self.rag_model.get_or_create_collection(new_name)

                # Move all documents to new collection
                docs = old_collection.collection.get()
                if docs["ids"]:
                    new_collection.collection.add(
                        documents=docs["documents"],
                        metadatas=docs["metadatas"],
                        ids=docs["ids"],
                    )

                # Delete old collection
                self.rag_model.chroma_client.delete_collection(self.current_collection)

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

    def get_messages(self, user_query, progress_callback=None):
        """Gets a RAG messages with multiple selected collections."""
        try:
            selected_ids = {}
            selected_collections = set()
            selected_items = self.data_store_tree.selection()

            if selected_items:
                document_refs = self.rag_model.get_document_refs()

                for item in selected_items:
                    if item.startswith("doc_"):
                        # Document selected
                        source_path = self.data_store_tree.item(item)["tags"][0]
                        collection_name = item.split("_")[
                            1
                        ]  # Extract collection name from item ID
                        selected_collections.add(collection_name)

                        # Get all document IDs associated with this source file
                        doc_ids = [
                            ref.document_id
                            for ref in document_refs.values()
                            if ref.source == source_path
                        ]
                        if collection_name not in selected_ids:
                            selected_ids[collection_name] = []
                        selected_ids[collection_name].extend(doc_ids)
                    elif item.startswith("collection_"):
                        # Entire collection selected
                        collection_name = item.split("_", 1)[1]
                        selected_collections.add(collection_name)

                        # Add all document IDs for the collection
                        for ref in document_refs.values():
                            if ref.collection_name == collection_name:
                                if collection_name not in selected_ids:
                                    selected_ids[collection_name] = []
                                selected_ids[collection_name].append(ref.document_id)

            return self.rag_model.get_init_messages(
                user_query=user_query,
                collection_names=list(selected_collections),  # Pass list of collections
                selected_ids=selected_ids,
                progress_callback=progress_callback,
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to get chat messages: {e}")

    def set_query(self):
        """Sets context to selected chat."""

        editor = RAGQueryEditor(
            self.parent,
            theme=self.theme,
            summarize_prompt=self.rag_model.summarize_prompt,
            context_prompt=self.rag_model.context_prompt,
        )
        if hasattr(self, "theme"):
            editor.apply_theme(theme=self.theme)

        def progress_callback(current, total):
            """Update the progress bar based on the progress_callback."""
            progress = int((current / total) * 100)
            editor.progress_bar["value"] = progress
            editor.progress_label.configure(
                text=f"Processing Progress: {current} of {total}"
            )
            editor.root.update_idletasks()

            if progress < 100:
                editor.root.after(100, self.parent)

        def on_save_callback(user_query, updated_summary, updated_context):
            self.rag_model.summarize_prompt = updated_summary
            self.rag_model.context_prompt = updated_context
            editor.progress_label.configure(text=f"Processing Progress: starting..")
            editor.root.update_idletasks()
            messages = self.get_messages(
                user_query, progress_callback=progress_callback
            )
            self.on_chat_start(messages)

        editor.on_save_callback = on_save_callback

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


class RAGQueryEditor:
    def __init__(self, parent, theme, summarize_prompt, context_prompt):
        """
        A window to edit summarize_prompt and context_prompt.

        Args:
            root: Parent Tkinter window.
            summarize_prompt: Initial value of the summarize_prompt.
            context_prompt: Initial value of the context_prompt.
            on_save_callback: Function to call when the user saves the changes.
        """
        self.root = tk.Toplevel(parent)
        self.root.title("Edit RAG Prompts and Query")

        # Create fields for summarize_prompt
        self.summary_label = tk.Label(self.root, text="Summarize Prompt:")
        self.summary_label.pack(anchor="w", padx=10, pady=(10, 0))

        self.summary_text = tk.Text(self.root, wrap=tk.WORD, height=10)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.summary_text.insert("1.0", summarize_prompt)

        # Create fields for context_prompt
        self.context_label = tk.Label(self.root, text="Context Prompt:")
        self.context_label.pack(anchor="w", padx=10, pady=(10, 0))

        self.context_text = tk.Text(self.root, wrap=tk.WORD, height=10)
        self.context_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.context_text.insert("1.0", context_prompt)

        # Create fields for user query
        self.query_label = tk.Label(self.root, text="User Query:")
        self.query_label.pack(anchor="w", padx=10, pady=(10, 0))

        self.query_text = tk.Text(self.root, wrap=tk.WORD, height=4)
        self.query_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.query_text.focus_set()

        # Progress Bar
        self.progress_frame = tk.Frame(self.root)
        self.progress_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.progress_label = tk.Label(
            self.progress_frame, text="Processing Progress: not started"
        )
        self.progress_label.pack(anchor="w")

        self.progress_bar = ttk.Progressbar(
            self.progress_frame, orient="horizontal", length=300, mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(fill=tk.X, pady=10)

        self.apply_button = tk.Button(
            self.button_frame, text="Apply", command=self.save
        )
        self.apply_button.pack(anchor="center")

        self.root.transient(parent)
        self.root.grab_set()

    def save(self):
        """Handle saving the updated prompts and user query."""
        user_query = self.query_text.get("1.0", tk.END).strip()
        updated_summary = self.summary_text.get("1.0", tk.END).strip()
        updated_context = self.context_text.get("1.0", tk.END).strip()

        if not user_query or not updated_summary or not updated_context:
            messagebox.showwarning(
                "Warning", "Please enter a query, summary and context."
            )
            return

        # Trigger the save callback with the updated values
        self.on_save_callback(user_query, updated_summary, updated_context)
        self.root.destroy()

    def apply_theme(self, theme):
        self.root.configure(bg=theme["bg"])

        self.summary_label.configure(bg=theme["bg"], fg=theme["fg"])
        self.summary_text.configure(
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            insertbackground=theme["input_fg"],
        )

        self.context_label.configure(bg=theme["bg"], fg=theme["fg"])
        self.context_text.configure(
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            insertbackground=theme["input_fg"],
        )

        self.query_label.configure(bg=theme["bg"], fg=theme["fg"])
        self.query_text.configure(
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            insertbackground=theme["input_fg"],
        )

        self.progress_frame.configure(bg=theme["bg"])
        self.progress_label.configure(bg=theme["bg"], fg=theme["fg"])
        self.progress_bar.configure(style="Horizontal.TProgressbar")

        self.button_frame.configure(bg=theme["bg"])
        self.apply_button.configure(
            bg=theme["button_bg"],
            fg=theme["button_fg"],
            activebackground=theme["button_bg_hover"],
            activeforeground=theme["button_fg"],
            relief="solid",
            borderwidth=1,
        )
