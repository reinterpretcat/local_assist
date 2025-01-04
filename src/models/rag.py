from dataclasses import dataclass
from typing import List, Iterator, Optional, Dict, Set
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader
import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
from ollama import Client
import os
from pathlib import Path
from .common import BaseModel


@dataclass
class DocumentReference:
    """Reference information for a document in a collection."""

    collection_name: str
    document_id: str
    source: str


class RAGCollection:
    def __init__(self, collection_name: str, chroma_client):
        self.name = collection_name
        self.collection = chroma_client.get_or_create_collection(name=collection_name)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def add_document(self, file_path: str, chunks: List[str]) -> List[str]:
        """Add document chunks to collection and return their IDs."""
        if not chunks:
            return []

        embeddings = self.model.encode(chunks, convert_to_numpy=True)

        # Generate unique IDs for this collection
        base_id = f"{self.name}_{os.path.basename(file_path)}".replace(" ", "_")
        chunk_ids = [f"{base_id}_{idx}" for idx in range(len(chunks))]

        # Always add as new documents since we want independent copies in each collection
        new_embeddings = [embedding.tolist() for embedding in embeddings]
        new_metadatas = [
            {
                "source": file_path,
                "id": chunk_id,
                "chunk_index": idx,
                "collection": self.name,
            }
            for idx, chunk_id in enumerate(chunk_ids)
        ]

        self.collection.add(
            ids=chunk_ids,
            documents=chunks,
            embeddings=new_embeddings,
            metadatas=new_metadatas,
        )

        return chunk_ids

    def query(
        self, query: str, top_k: int, selected_ids: Optional[List[str]] = None
    ) -> Dict:
        """Query the collection with optional document filtering."""
        query_embedding = self.model.encode([query])[0]

        # If specific documents are selected, use where filter
        where = {"id": {"$in": selected_ids}} if selected_ids else None

        return self.collection.query(
            query_embeddings=[query_embedding.tolist()], n_results=top_k, where=where
        )

    def get_documents(self) -> Set[str]:
        """Get all unique document sources in this collection."""
        results = self.collection.get(include=["metadatas"])
        return {metadata["source"] for metadata in results["metadatas"]}


class RAG(BaseModel):
    def __init__(self, **kwargs) -> None:
        """A class for Retrieval Augmented Generation using the ollama library."""
        super().__init__(**kwargs)

        self.ollama_client = Client()
        self.chroma_client = chromadb.PersistentClient(
            path=kwargs.get("persist_directory"),
            settings=Settings(allow_reset=True, is_persistent=True),
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE,
        )

        # Dictionary to store all collections
        self.collections: Dict[str, RAGCollection] = {}

        # Dictionary to store document references
        self.document_refs: Dict[str, DocumentReference] = {}

        # Load existing collections and document refs
        self._load_existing_collections_and_refs()

        # Initialize default collection
        self.get_or_create_collection("default")

    def _load_existing_collections_and_refs(self):
        """Load existing collections and document references from the ChromaDB client."""
        try:
            existing_collections = self.chroma_client.list_collections()

            for collection_name in existing_collections:
                # Initialize the collection
                collection = RAGCollection(collection_name, self.chroma_client)
                self.collections[collection_name] = collection

                # Load document references from the metadata
                metadatas = collection.collection.get(include=["metadatas"])[
                    "metadatas"
                ]
                for metadata in metadatas:
                    document_id = metadata.get("id")
                    source = metadata.get("source")
                    if document_id and source:
                        self.document_refs[document_id] = DocumentReference(
                            collection_name=collection_name,
                            document_id=document_id,
                            source=source,
                        )

        except Exception as e:
            print(f"Error loading existing collections or document references: {e}")

    def get_or_create_collection(self, collection_name: str) -> RAGCollection:
        """Get or create a RAG collection."""
        if collection_name not in self.collections:
            self.collections[collection_name] = RAGCollection(
                collection_name, self.chroma_client
            )
        return self.collections[collection_name]

    def get_collections(self) -> List[str]:
        """Get list of available collections."""
        return list(self.collections.keys())

    def get_document_refs(self) -> Dict[str, DocumentReference]:
        """Get all document references."""
        return self.document_refs

    def get_collection_documents(self, collection_name: str) -> List[Dict]:
        """Get all documents in a collection."""
        if collection_name not in self.collections:
            return []

        collection = self.collections[collection_name]
        results = collection.collection.get(include=["metadatas"])
        return results["metadatas"]

    def add_document(
        self, collection_name: str, file_path: str, document_type: str = None
    ):
        """Add a document to a specific collection."""
        if document_type is None:
            document_type = Path(file_path).suffix.lower()

        # Get document chunks based on type
        chunks = self._get_document_chunks(file_path, document_type)

        # Get or create collection and add document
        collection = self.get_or_create_collection(collection_name)
        chunk_ids = collection.add_document(file_path, chunks)

        # Store document references - now specific to this collection
        for chunk_id in chunk_ids:
            self.document_refs[chunk_id] = DocumentReference(
                collection_name=collection_name, document_id=chunk_id, source=file_path
            )

    def _get_document_chunks(self, file_path: str, document_type: str) -> List[str]:
        """Get chunks from document based on its type."""
        if document_type in [".pdf", "pdf"]:
            reader = PdfReader(file_path)
            return [page.extract_text() for page in reader.pages if page.extract_text()]

        elif document_type in [".md", "md", "markdown"]:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content.split("\n\n")

        else:  # Default to text processing
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().split("\n\n")

    def retrieve_and_limit_context(
        self,
        query: str,
        collection_name: str = None,
        selected_ids: List[str] = None,
        top_k: int = 10,
        token_limit: int = 1500,
        min_relevance: float = 0.3,
    ) -> List[str]:
        """Retrieve and filter relevant chunks based on token limits."""
        if collection_name and collection_name in self.collections:
            collections_to_query = [self.collections[collection_name]]
        else:
            collections_to_query = list(self.collections.values())

        all_chunks = []
        for collection in collections_to_query:
            results = collection.query(query, top_k, selected_ids)

            # Combine results with metadata and scores
            for idx, (chunk, metadata, distance) in enumerate(
                zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ):
                relevance_score = 1 - (
                    distance / 2
                )  # Convert cosine distance to similarity
                if relevance_score >= min_relevance:
                    all_chunks.append(
                        {
                            "text": chunk,
                            "tokens": len(chunk.split()),
                            "relevance": relevance_score,
                            "metadata": metadata,
                            "index": idx,
                        }
                    )

        # Sort chunks by relevance
        all_chunks = sorted(all_chunks, key=lambda x: x["relevance"], reverse=True)

        # Select chunks while respecting token limits
        selected_chunks = []
        total_tokens = 0

        for chunk in all_chunks:
            if total_tokens + chunk["tokens"] <= token_limit:
                selected_chunks.append(chunk["text"])
                total_tokens += chunk["tokens"]
            else:
                break

        return selected_chunks

    def summarize_chunks(self, chunks: List[str], token_limit: int = 1500) -> str:
        """Summarize the retrieved chunks if their combined length exceeds the token limit."""
        prompt = "Summarize the following information concisely:\n\n" + "\n\n".join(
            chunks
        )
        response = self.ollama_client.chat([{"role": "user", "content": prompt}])

        # Ensure the summary fits within the token limit
        summary = response["content"]
        if len(summary.split()) > token_limit:
            summary = " ".join(summary.split()[:token_limit]) + "..."
        return summary

    def forward(
        self,
        user_query: str,
        collection_name: str = None,
        selected_ids: List[str] = None,
        token_limit: int = 1500,
    ) -> Iterator[str]:
        """Generate a response using RAG with filtered and optimized context."""
        context_chunks = self.retrieve_and_limit_context(
            query=user_query,
            collection_name=collection_name,
            selected_ids=selected_ids,
            top_k=10,
            token_limit=token_limit,
            min_relevance=0.1,
        )

        # Summarize chunks if the combined length exceeds token_limit
        total_tokens = sum(len(chunk.split()) for chunk in context_chunks)
        if total_tokens > token_limit:
            context_chunks = [
                self.summarize_chunks(context_chunks, token_limit=token_limit)
            ]

        print(f"{context_chunks=}")

        # Construct the prompt
        prompt = (
            f"[CONTEXT]\n{'\n'.join(context_chunks)}\n\n"
            f"[QUERY]\n{user_query}\n\n"
            f"[INSTRUCTION]\nAnswer based on the provided context."
        )

        # Generate response token by token
        stream = self.ollama_client.chat(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        for chunk in stream:
            yield chunk["message"]["content"]
