import tkinter as tk
import os
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict
from .models import RAG, DocumentReference


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

        # Collection selection dropdown
        self.collection_var = tk.StringVar()
        self.collection_dropdown = ttk.Combobox(
            self.collection_frame, textvariable=self.collection_var, state="readonly"
        )
        self.collection_dropdown.pack(side=tk.LEFT, padx=5, pady=5)
        self.collection_dropdown.bind(
            "<<ComboboxSelected>>", self.on_collection_changed
        )

        # New collection button
        self.new_collection_button = ttk.Button(
            self.collection_frame,
            text="New Collection",
            command=self.create_new_collection,
        )
        self.new_collection_button.pack(side=tk.LEFT, padx=5, pady=5)

        # File Upload Section
        self.upload_frame = ttk.LabelFrame(self.window, text="Upload Documents")
        self.upload_frame.pack(fill=tk.X, padx=10, pady=5)

        self.upload_button = ttk.Button(
            self.upload_frame, text="Upload File", command=self.upload_file
        )
        self.upload_button.pack(side=tk.LEFT, padx=5, pady=5)

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

        self.refresh_button = ttk.Button(
            self.data_store_frame, text="Refresh", command=self.refresh_data_store
        )
        self.refresh_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.delete_button = ttk.Button(
            self.data_store_frame, text="Delete Selected", command=self.delete_selected
        )
        self.delete_button.pack(side=tk.LEFT, padx=5, pady=5)

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
        self.refresh_collections()
        self.refresh_data_store()

    def refresh_collections(self):
        """Refresh the collections dropdown."""
        collections = self.rag_model.get_collections()
        self.collection_dropdown["values"] = collections
        if collections and not self.collection_var.get():
            self.collection_var.set(collections[0])
            self.current_collection = collections[0]

    def create_new_collection(self):
        """Create a new collection."""
        name = tk.simpledialog.askstring("New Collection", "Enter collection name:")
        if name:
            try:
                self.rag_model.get_or_create_collection(name)
                self.refresh_collections()
                self.collection_var.set(name)
                self.current_collection = name
                self.refresh_data_store()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create collection: {e}")

    def on_collection_changed(self, event):
        """Handle collection selection change."""
        self.current_collection = self.collection_var.get()
        self.refresh_data_store()

    def upload_file(self):
        """Handle file uploads."""
        if not self.current_collection:
            messagebox.showwarning(
                "Warning", "Please select or create a collection first."
            )
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
            self.rag_model.add_document(
                collection_name=self.current_collection, file_path=file_path
            )
            self.refresh_data_store()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload file: {e}")

    def refresh_data_store(self):
        """Refresh the data store display with hierarchical view."""
        self.data_store_tree.delete(*self.data_store_tree.get_children())

        try:
            document_refs = self.rag_model.get_document_refs()
            collections_dict = {}

            # First, group by collection and source file
            for doc_ref in document_refs.values():
                if doc_ref.collection_name not in collections_dict:
                    collections_dict[doc_ref.collection_name] = {}

                # Use source file as key to prevent duplicates
                collections_dict[doc_ref.collection_name][doc_ref.source] = doc_ref

            # Add collections and their documents
            for collection_name, docs_dict in collections_dict.items():
                collection_id = f"collection_{collection_name}"
                self.data_store_tree.insert(
                    "", tk.END, iid=collection_id, text=collection_name, values=("", "")
                )

                # Add unique documents under collection
                for source_path, doc_ref in docs_dict.items():
                    file_name = os.path.basename(source_path)
                    file_type = os.path.splitext(source_path)[1][1:].upper()
                    doc_id = f"doc_{hash(source_path)}"

                    self.data_store_tree.insert(
                        collection_id,
                        tk.END,
                        iid=doc_id,
                        tags=(source_path,),
                        values=(file_name, file_type),
                    )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh data store: {e}")

    def delete_selected(self):
        """Delete selected documents."""
        selected_items = self.data_store_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "No document selected.")
            return

        try:
            for item in selected_items:
                if item.startswith("collection_"):
                    continue

                # Get source path from tags
                source_path = self.data_store_tree.item(item)["tags"][0]
                parent_id = self.data_store_tree.parent(item)
                collection_name = parent_id.replace("collection_", "")

                collection = self.rag_model.get_or_create_collection(collection_name)
                collection.collection.delete(where={"source": source_path})
            self.refresh_data_store()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete documents: {e}")

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
                            source_path = self.data_store_tree.item(item)['tags'][0]
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
