import tkinter as tk
import os
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict
from .models import RAG, DocumentReference


class RAGManagementUI:
    def __init__(self, parent, rag: RAG):
        """Initialize the RAG Management UI."""
        self.parent = parent
        self.rag_model = rag
        self.current_collection: Optional[str] = None

        # Create the RAG Management window
        self.window = tk.Toplevel(parent)
        self.window.title("RAG Management")
        self.window.geometry("1024x786")
        self.window.transient(parent)
        self.window.grab_set()

        # Collection Management Section
        self.collection_frame = ttk.LabelFrame(
            self.window, text="Collection Management"
        )
        self.collection_frame.pack(fill=tk.X, padx=10, pady=5)

        # Collection management buttons
        self.new_collection_button = ttk.Button(
            self.collection_frame,
            text="New Collection",
            command=self.create_new_collection,
        )
        self.new_collection_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.rename_collection_button = ttk.Button(
            self.collection_frame,
            text="Rename Collection",
            command=self.rename_collection,
        )
        self.rename_collection_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.delete_button = ttk.Button(
            self.collection_frame, text="Delete Selected", command=self.delete_selected
        )
        self.delete_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Data Store Section
        self.data_store_frame = ttk.LabelFrame(self.window, text="Data Store")
        self.data_store_frame.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)

        # Create a frame to hold the Treeview and scrollbars
        self.tree_frame = ttk.Frame(self.data_store_frame)
        self.tree_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        # Configure style for proper row height
        style = ttk.Style()
        style.configure(
            "Treeview",
            rowheight=36,
            font=("TkDefaultFont", 10),
        )

        # Modified Treeview structure
        self.data_store_tree = ttk.Treeview(
            self.tree_frame,
            columns=("Name", "Type"),
            show="tree headings",
            style="Treeview",
            selectmode="extended",
        )
        self.data_store_tree.heading("Name", text="File Name")
        self.data_store_tree.heading("Type", text="File Type")

        # Set column widths
        self.data_store_tree.column("Name", width=500, minwidth=200)
        self.data_store_tree.column("Type", width=100, minwidth=80)

        # Create vertical scrollbar
        self.vsb = ttk.Scrollbar(
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

        self.upload_button = ttk.Button(
            self.data_store_frame, text="Upload File", command=self.upload_file
        )
        self.upload_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.refresh_button = ttk.Button(
            self.data_store_frame, text="Refresh", command=self.refresh_data_store
        )
        self.refresh_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Query Testing Section
        self.query_frame = ttk.LabelFrame(self.window, text="Test RAG Query")
        self.query_frame.pack(fill=tk.X, padx=10, pady=5)

        self.query_entry = ttk.Entry(self.query_frame, width=70)
        self.query_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.use_selected_var = tk.BooleanVar(value=False)
        self.use_selected_checkbox = ttk.Checkbutton(
            self.query_frame, text="Query Selected Only", variable=self.use_selected_var
        )
        self.use_selected_checkbox.pack(side=tk.LEFT, padx=5, pady=5)

        self.query_button = ttk.Button(
            self.query_frame, text="Test Query", command=self.test_query
        )
        self.query_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.query_result = tk.Text(
            self.window, wrap=tk.WORD, height=8, state=tk.DISABLED, bg="#f9f9f9"
        )
        self.query_result.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)

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

    def test_query(self):
        """Test a RAG query."""
        query = self.query_entry.get()
        if not query:
            messagebox.showwarning("Warning", "Please enter a query.")
            return

        try:
            selected_ids = None
            if self.use_selected_var.get():
                selected_items = self.data_store_tree.selection()
                if selected_items:
                    selected_ids = []
                    document_refs = self.rag_model.get_document_refs()

                    for item in selected_items:
                        if item.startswith("doc_"):
                            source_path = self.data_store_tree.item(item)["tags"][0]
                            # Get all document IDs associated with this source file
                            doc_ids = [
                                ref.document_id
                                for ref in document_refs.values()
                                if ref.source == source_path
                            ]
                            selected_ids.extend(doc_ids)

            generator = self.rag_model.forward(
                user_query=query,
                collection_name=self.current_collection,
                selected_ids=selected_ids,
            )

            self.query_result.config(state=tk.NORMAL)
            self.query_result.delete(1.0, tk.END)

            def process_tokens():
                try:
                    token = next(generator)
                    self.query_result.insert(tk.END, token)
                    self.query_result.see(tk.END)
                    self.query_result.after(10, process_tokens)
                except StopIteration:
                    self.query_result.config(state=tk.DISABLED)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to stream tokens: {e}")
                    self.query_result.config(state=tk.DISABLED)

            process_tokens()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to test query: {e}")
