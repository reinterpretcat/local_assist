import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import tkinter.filedialog as filedialog
from typing import Dict, Optional
from pathlib import Path
from llama_index.core.vector_stores import (
    MetadataFilters,
    ExactMatchFilter,
    FilterCondition,
)

from ..tools import (
    get_list_style,
    get_scrollbar_style,
    get_button_config,
    get_combobox_style,
)
from ..models import RAG


class DocumentManagerGUI(tk.Toplevel):
    def __init__(self, root, rag: RAG, theme: Dict):
        super().__init__(root)
        self.rag = rag
        self.title("Document Collection Manager")

        # Allow resizing in both directions
        self.resizable(True, True)
        # Set the size of the new window based on the parent window size
        new_width = int(root.winfo_width() * 0.75)
        new_height = int(root.winfo_height() * 0.95)
        self.geometry(f"{new_width}x{new_height}")

        self.setup_gui()
        self.load_collections()
        self.apply_theme(theme)

    def setup_gui(self):
        # Top frame for collection selection
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(fill="x", padx=5, pady=5)

        self.collection_label = tk.Label(self.top_frame, text="Collection:")
        self.collection_label.pack(side="left")

        self.collection_var = tk.StringVar()
        self.collection_combo = ttk.Combobox(
            self.top_frame, textvariable=self.collection_var
        )
        self.collection_combo.pack(side="left", padx=5)
        self.collection_combo.bind("<<ComboboxSelected>>", self.on_collection_selected)

        self.add_documents_button = tk.Button(
            self.top_frame, text="📂 Add Documents", command=self.add_documents
        )
        self.add_documents_button.pack(side="right")

        # Main paned window for resizable panels
        self.paned_window = ttk.PanedWindow(self, orient="horizontal")
        self.paned_window.pack(fill="both", expand=True, padx=5, pady=5)

        # Setup panels
        self.setup_file_tree()
        self.setup_document_list()

        # Bottom frame for document content
        self.setup_document_content()

    def setup_file_tree(self):
        self.tree_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.tree_frame, weight=1)

        self.file_structure_label = tk.Label(self.tree_frame, text="File Structure")
        self.file_structure_label.pack(fill="x")

        # Create frame for tree with scrollbars
        self.tree_container = tk.Frame(self.tree_frame)
        self.tree_container.pack(fill="both", expand=True)

        self.file_tree = ttk.Treeview(self.tree_container, selectmode="browse")

        # Add scrollbars
        self.file_v_scroll = ttk.Scrollbar(
            self.tree_container, orient="vertical", command=self.file_tree.yview
        )
        self.file_h_scroll = ttk.Scrollbar(
            self.tree_container, orient="horizontal", command=self.file_tree.xview
        )

        # Configure tree
        self.file_tree.configure(
            yscrollcommand=self.file_v_scroll.set, xscrollcommand=self.file_h_scroll.set
        )

        # Grid layout for tree and scrollbars
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        self.file_v_scroll.grid(row=0, column=1, sticky="ns")
        self.file_h_scroll.grid(row=1, column=0, sticky="ew")

        # Configure grid weights
        self.tree_container.grid_rowconfigure(0, weight=1)
        self.tree_container.grid_columnconfigure(0, weight=1)

        self.file_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Buttons
        self.tree_buttons_frame = tk.Frame(self.tree_frame)
        self.tree_buttons_frame.pack(fill="x", pady=5)

        self.tree_context_button = tk.Button(
            self.tree_buttons_frame,
            text="🔍 Retrieve Context",
            command=self.get_tree_context,
        )
        self.tree_context_button.pack(side="left", padx=5)

        self.tree_delete_button = tk.Button(
            self.tree_buttons_frame,
            text="🗑️ Delete Selected",
            command=self.delete_tree_selection,
        )
        self.tree_delete_button.pack(side="right")

    def setup_document_list(self):
        self.list_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.list_frame, weight=2)

        self.documents_label = tk.Label(self.list_frame, text="Documents")
        self.documents_label.pack(fill="x")

        # Create frame for list with scrollbars
        self.list_container = tk.Frame(self.list_frame)
        self.list_container.pack(fill="both", expand=True)

        columns = ("id", "source", "created_at", "chunk_index", "total_chunks")
        self.doc_list = ttk.Treeview(
            self.list_container, columns=columns, show="headings"
        )

        # Add scrollbars
        self.document_v_scroll = ttk.Scrollbar(
            self.list_container, orient="vertical", command=self.doc_list.yview
        )
        self.document_h_scroll = ttk.Scrollbar(
            self.list_container, orient="horizontal", command=self.doc_list.xview
        )

        # Configure list
        self.doc_list.configure(
            yscrollcommand=self.document_v_scroll.set,
            xscrollcommand=self.document_h_scroll.set,
        )

        # Grid layout
        self.doc_list.grid(row=0, column=0, sticky="nsew")
        self.document_v_scroll.grid(row=0, column=1, sticky="ns")
        self.document_h_scroll.grid(row=1, column=0, sticky="ew")

        # Configure grid weights
        self.list_container.grid_rowconfigure(0, weight=1)
        self.list_container.grid_columnconfigure(0, weight=1)

        for col in columns:
            self.doc_list.heading(col, text=col.replace("_", " ").title())

        self.doc_list.bind("<<TreeviewSelect>>", self.on_document_select)

        # Buttons
        self.list_buttons_frame = tk.Frame(self.list_frame)
        self.list_buttons_frame.pack(fill="x", pady=5)
        self.list_delete_button = tk.Button(
            self.list_buttons_frame,
            text="🗑️ Delete Selected",
            command=self.delete_document,
        )
        self.list_delete_button.pack(side="right")

    def setup_document_content(self):
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.document_content_label = tk.Label(self.content_frame, text="Content")
        self.document_content_label.pack()

        self.content_text = tk.Text(self.content_frame, wrap="word", height=10)
        self.content_text.pack(fill="both", expand=True)

    def load_collections(self):
        collections = self.rag.list_collections()
        collection_names = [c["name"] for c in collections]
        self.collection_combo["values"] = collection_names
        if collection_names:
            self.collection_combo.set(collection_names[0])
            self.on_collection_selected(None)

    def build_file_tree(self, collection_name, doc_path: Path = None):
        self.file_tree.delete(*self.file_tree.get_children())
        collection = self.rag.get_collection(collection_name)
        result = collection.get(include=["metadatas"])

        paths = {}

        for meta in result["metadatas"]:
            if not meta or "file_path" not in meta:
                continue

            path = Path(meta["file_path"])
            if doc_path is None:
                doc_path = path

            current = ""
            for part in path.parts:
                parent = current
                current = str(Path(current) / part)
                if current not in paths:
                    paths[current] = self.file_tree.insert(
                        paths.get(parent, ""), "end", text=part, values=(current,)
                    )

        # Expand to document
        if doc_path:
            current_path = ""
            for part in doc_path.parts[:-1]:  # Exclude file name
                current_path = str(Path(current_path) / part)
                item_id = paths.get(current_path)
                if item_id:
                    self.file_tree.see(item_id)
                    self.file_tree.item(item_id, open=True)

    def update_document_list(self, path_filter: Optional[str] = None):
        self.doc_list.delete(*self.doc_list.get_children())
        collection = self.rag.get_collection(self.collection_var.get())

        result = collection.get(include=["metadatas"])
        metadatas = result["metadatas"]

        for meta in metadatas:
            if not meta or "file_path" not in meta:
                continue
            if not path_filter or path_filter in meta["file_path"]:
                values = (
                    meta.get("id", ""),
                    meta.get("source", ""),
                    meta.get("created_at", ""),
                    meta.get("chunk_index", ""),
                    meta.get("total_chunks", ""),
                )
                self.doc_list.insert("", "end", values=values)

    def on_collection_selected(self, event):
        collection = self.collection_var.get()
        if collection:
            self.build_file_tree(collection)
            self.update_document_list()

    def on_tree_select(self, event):
        selected = self.file_tree.selection()
        if selected:
            path = self.file_tree.item(selected[0])["values"][0]
            self.update_document_list(path)

    def on_document_select(self, event):
        selected = self.doc_list.selection()
        if selected:
            doc_id = self.doc_list.item(selected[0])["values"][0]
            collection = self.rag.get_collection(self.collection_var.get())
            result = collection.get(ids=[doc_id])

            self.content_text.delete("1.0", tk.END)
            if result["documents"]:
                self.content_text.insert("1.0", result["documents"][0])

    def delete_document(self):
        selected = self.doc_list.selection()
        if selected:
            if messagebox.askyesno("Confirm", "Delete selected document(s)?"):
                collection = self.rag.get_collection(self.collection_var.get())
                for item in selected:
                    doc_id = self.doc_list.item(item)["values"][0]
                    collection.delete(ids=[doc_id])

                tree_selected = self.file_tree.selection()
                path = None
                if tree_selected:
                    path = self.file_tree.item(tree_selected[0])["values"][0]
                self.build_file_tree(self.collection_var.get(), doc_path=Path(path))
                self.update_document_list()

    def delete_tree_selection(self):
        selected = self.file_tree.selection()
        if selected:
            path = self.file_tree.item(selected[0])["values"][0]
            if messagebox.askyesno("Confirm", f"Delete all documents in {path}?"):
                collection = self.rag.get_collection(self.collection_var.get())
                result = collection.get(include=["metadatas"])
                to_delete = [
                    meta["id"]
                    for meta in result["metadatas"]
                    if path in meta["file_path"]
                ]
                if to_delete:
                    collection.delete(ids=to_delete)
                    self.build_file_tree(self.collection_var.get(), doc_path=Path(path))
                    self.update_document_list()

    def get_tree_context(self):
        selected = self.file_tree.selection()
        if selected:
            path = self.file_tree.item(selected[0])["values"][0]
            collection = self.rag.get_collection(self.collection_var.get())
            result = collection.get(include=["metadatas"])
            file_paths = [
                meta["file_path"]
                for meta in result["metadatas"]
                if path in meta["file_path"]
            ]

            metadata_filters = (
                MetadataFilters(
                    filters=[
                        ExactMatchFilter(key="file_path", value=file_path)
                        for file_path in file_paths
                    ],
                    condition=FilterCondition.OR,
                )
                if len(file_paths) > 0
                else None
            )

            if file_paths:
                query = simpledialog.askstring("Query Input", "Enter your query:")
                if query:
                    context = self.rag.retrieve_context(
                        query=query,
                        collection_name=self.collection_var.get(),
                        metadata_filters=metadata_filters,
                    )
                    # self.show_context_window(context)
                    self.content_text.delete("1.0", tk.END)
                    self.content_text.insert("1.0", context)

    def add_documents(self):
        collection = self.collection_var.get()
        if not collection:
            messagebox.showerror("Error", "Please select a collection first")
            return

        path = filedialog.askdirectory()
        if path:
            self.rag.add_documents(path, collection)
            self.build_file_tree(collection)
            self.update_document_list()

    def apply_theme(self, theme: Dict):
        self.theme = theme

        self.config(bg=theme["bg"], borderwidth=1, relief="solid")

        style = ttk.Style()
        style.configure("RAG.TPanedwindow", background=theme["bg"])
        self.paned_window.configure(style="RAG.TPanedwindow")

        button_config = get_button_config(theme)
        for button in [
            self.tree_delete_button,
            self.tree_context_button,
            self.list_delete_button,
            self.add_documents_button,
        ]:
            button.configure(**button_config)

        for frame in [
            self.top_frame,
            self.list_frame,
            self.tree_frame,
            self.content_frame,
            self.tree_buttons_frame,
            self.list_buttons_frame,
            self.tree_container,
            self.list_container,
        ]:
            frame.configure(bg=theme["bg"], borderwidth=1, relief="solid")

        for label in [
            self.file_structure_label,
            self.documents_label,
            self.collection_label,
            self.document_content_label,
        ]:
            label.configure(bg=theme["bg"], fg=theme["fg"], font=("TkDefaultFont", 10))

        style = get_list_style(theme=theme)
        self.file_tree.configure(style="Treeview")
        self.doc_list.configure(style="Treeview")

        _ = get_combobox_style(theme)
        self.collection_combo.option_add(
            "*TCombobox*Listbox.background", theme["input_bg"]
        )
        self.collection_combo.option_add(
            "*TCombobox*Listbox.foreground", theme["input_fg"]
        )
        self.collection_combo.option_add(
            "*TCombobox*Listbox.selectBackground", theme["popup_bg"]
        )
        self.collection_combo.option_add(
            "*TCombobox*Listbox.selectForeground", theme["fg"]
        )

        self.content_text.configure(
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            insertbackground=theme["input_fg"],
        )

        _ = get_scrollbar_style(theme)
        self.document_h_scroll.configure(style="Horizontal.CustomScrollbar.TScrollbar")
        self.document_v_scroll.configure(style="Vertical.CustomScrollbar.TScrollbar")
        self.file_h_scroll.configure(style="Horizontal.CustomScrollbar.TScrollbar")
        self.file_v_scroll.configure(style="Vertical.CustomScrollbar.TScrollbar")
