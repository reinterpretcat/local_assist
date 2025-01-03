import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .models import RAG


class RAGManagementUI:
    def __init__(self, parent, rag: RAG):
        """Initialize the RAG Management UI."""
        self.parent = parent
        self.rag_model = rag

        # Create the RAG Management window
        self.window = tk.Toplevel(parent)
        self.window.title("RAG Management")
        self.window.geometry("1024x786")
        self.window.transient(parent)  # Make the RAG window modal
        self.window.grab_set()  # Ensure focus stays on the RAG wind

        # File Upload Section
        self.upload_frame = ttk.LabelFrame(self.window, text="Upload Documents")
        self.upload_frame.pack(fill=tk.X, padx=10, pady=10)

        self.upload_button = ttk.Button(
            self.upload_frame, text="Upload File", command=self.upload_file
        )
        self.upload_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Data Store Section
        self.data_store_frame = ttk.LabelFrame(self.window, text="Data Store")
        self.data_store_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)

        # Create a frame to hold the Treeview and scrollbars
        self.tree_frame = ttk.Frame(self.data_store_frame)
        self.tree_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        # Configure style for proper row height
        style = ttk.Style()
        style.configure(
            "Treeview",
            rowheight=36,  # Increased row height
            font=("TkDefaultFont", 10),  # Explicit font size
        )

        self.data_store_tree = ttk.Treeview(
            self.tree_frame,
            columns=("Name", "Type"),
            show="headings",
            style="Treeview",  # Apply the style
        )
        self.data_store_tree.heading("Name", text="File Name")
        self.data_store_tree.heading("Type", text="File Type")

        # Set column widths
        self.data_store_tree.column("Name", width=640, minwidth=320)
        self.data_store_tree.column("Type", width=48, minwidth=24)

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
        self.query_frame.pack(fill=tk.X, padx=10, pady=10)

        self.query_entry = ttk.Entry(self.query_frame, width=70)
        self.query_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.query_button = ttk.Button(
            self.query_frame, text="Test Query", command=self.test_query
        )
        self.query_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.query_result = tk.Text(
            self.window, wrap=tk.WORD, height=8, state=tk.DISABLED, bg="#f9f9f9"
        )
        self.query_result.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)

        self.refresh_data_store()

    def upload_file(self):
        """Handle file uploads."""
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
            if file_path.endswith(".txt"):
                self.rag_model.add_text(file_path)
            elif file_path.endswith(".md"):
                self.rag_model.add_markdown(file_path)
            elif file_path.endswith(".pdf"):
                self.rag_model.add_pdf(file_path)
            else:
                messagebox.showerror("Error", "Unsupported file type.")
                return

            self.refresh_data_store()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload file: {e}")

    def refresh_data_store(self):
        """Refresh the data store display, showing files instead of individual chunks."""
        self.data_store_tree.delete(*self.data_store_tree.get_children())

        # Fetch metadata from the collection
        try:
            results = self.rag_model.collection.get(include=["metadatas"])
            metadatas = results.get("metadatas", [])

            # Aggregate by file name (source)
            files = set(meta["source"] for meta in metadatas if "source" in meta)

            # Populate the treeview with file names
            for file_name in files:
                self.data_store_tree.insert("", tk.END, values=(file_name, "File"))
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
                file_name = self.data_store_tree.item(item, "values")[0]
                self.rag_model.collection.delete(where={"source": file_name})
            self.refresh_data_store()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete documents: {e}")

    def test_query(self):
        """Test a RAG query with meaningful summarization."""
        query = self.query_entry.get()
        if not query:
            messagebox.showwarning("Warning", "Please enter a query.")
            return

        try:
            generator = self.rag_model.forward(query)

            # Clear the result area
            self.query_result.config(state=tk.NORMAL)
            self.query_result.delete(1.0, tk.END)

            def process_tokens():
                try:
                    # Get the next token
                    token = next(generator)
                    self.query_result.insert(tk.END, token)
                    self.query_result.see(tk.END)  # Auto-scroll to the bottom

                    # Schedule the next token processing
                    self.query_result.after(10, process_tokens)
                except StopIteration:
                    # All tokens have been received
                    self.query_result.config(state=tk.DISABLED)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to stream tokens: {e}")
                    self.query_result.config(state=tk.DISABLED)

            # Start processing tokens
            process_tokens()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to test query: {e}")
