from dataclasses import dataclass
from typing import List, Iterator, Optional, Dict, Set
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader
import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
from ollama import Client, Options
import os
from pathlib import Path
from .common import BaseModel
import logging
from colorama import Fore
from ..utils import print_system_message


@dataclass
class DocumentReference:
    """Reference information for a document in a collection."""

    collection_name: str
    document_id: str
    source: str


class RAGCollection:
    def __init__(self, collection_name: str, chroma_client):
        self.name = collection_name
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        self.collection = chroma_client.get_or_create_collection(
            name=collection_name,
            # https://docs.trychroma.com/docs/collections/configure
            metadata={
                # use cosine similarity metric while default is Squared L2
                "hnsw:space": "cosine",
                # determines the size of the dynamic candidate list used while searching for the nearest neighbors.
                # A higher value improves recall and accuracy by exploring more potential neighbors but increases
                # query time and computational cost, while a lower value results in faster but less accurate searches.
                # The default value is 10.
                "hnsw:search_ef": 30,
            },
        )

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

    def __repr__(self):
        return self.name

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


class ContextManager:
    def __init__(self, **kwargs):

        self.token_limit = int(kwargs.get("token_limit"))
        self.min_relevance = float(kwargs.get("min_relevance"))
        self.top_k = int(kwargs.get("top_k"))

    def get_context_text(
        self,
        user_query: str,
        summarize_prompt: str,
        collections: List[RAGCollection],
        selected_ids: List[str],
        chat_callback,
    ):

        context_chunks = self._retrieve_and_limit_context(
            query=user_query,
            collections=collections,
            selected_ids=selected_ids,
        )
        
        print_system_message(f"raw {len(context_chunks)=}")

        # Summarize chunks if the combined length exceeds token_limit
        total_tokens = sum(len(chunk.split()) for chunk in context_chunks)
        if total_tokens > self.token_limit:
            context_chunks = [
                self._summarize_chunks(
                    summarize_prompt,
                    context_chunks,
                    chat_callback=chat_callback,
                )
            ]
            
        print_system_message(f"final {len(context_chunks)=}")

        return "\n".join(context_chunks)

    def _retrieve_and_limit_context(
        self,
        query: str,
        collections: List[RAGCollection] = None,
        selected_ids: List[str] = None,
    ) -> List[str]:
        """Retrieve and filter relevant chunks while preserving their natural order."""

        all_chunks = []
        for collection in collections:
            # Filter selected IDs for this collection
            ids_to_query = selected_ids.get(collection.name) if selected_ids else None
            results = collection.query(query, self.top_k, ids_to_query)

            for idx, (chunk, metadata, distance) in enumerate(
                zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ):
                relevance_score = 1 - (distance / 2)
                if relevance_score >= self.min_relevance:
                    all_chunks.append(
                        {
                            "text": chunk,
                            "tokens": len(chunk.split()),
                            "relevance": relevance_score,
                            "metadata": metadata,
                            "source": metadata.get("source", "unknown"),
                            "source_position": metadata.get("chunk_index", idx),
                        }
                    )
        
        print_system_message(f"{len(all_chunks)=}")

        return self._group_context_chunks(all_chunks)

    def _summarize_chunks(
        self, summarize_prompt, chunks: List[str], chat_callback
    ) -> str:
        """Summarize the retrieved chunks."""

        messages = [
            {"role": "system", "content": summarize_prompt},
            {
                "role": "user",
                "content": f"Summarize while preserving context, dialogue, and language style:\n\n{'\n\n'.join(chunks)}",
            },
        ]

        response = chat_callback(messages)

        # Post-process the summary to ensure quality
        summary = self._post_process_chunk_summary(response)

        if len(summary.split()) > self.token_limit:
            summary = " ".join(summary.split()[: self.token_limit]) + "..."

        return summary

    def _group_context_chunks(self, all_chunks):
        """Group chunks by source and sort them."""
        grouped_chunks = {}
        for chunk in all_chunks:
            source = chunk["source"]
            if source not in grouped_chunks:
                grouped_chunks[source] = []
            grouped_chunks[source].append(chunk)

        for source in grouped_chunks:
            grouped_chunks[source].sort(key=lambda x: x["source_position"])

        selected_text = []
        selected_total_tokens = 0

        for source in grouped_chunks:
            for chunk in grouped_chunks[source]:
                selected_text.append(chunk["text"])
                selected_total_tokens += chunk["tokens"]

        print_system_message(f"{len(selected_text)=}")
        print_system_message(f"{selected_total_tokens=}")

        return selected_text

    def _post_process_chunk_summary(self, summary: str) -> str:
        """Clean up and improve the summary"""
        processed_summary = summary

        # TODO do some modifications to have better structured and cleaned up text

        return processed_summary


class RAG(BaseModel):
    def __init__(self, **kwargs) -> None:
        """A class for Retrieval Augmented Generation using the ollama library."""
        super().__init__(**kwargs)

        self.summarize_prompt = kwargs.get("summarize_prompt")
        self.context_prompt = kwargs.get("context_prompt")

        self.context_manager = ContextManager(**kwargs)

        self.ollama_client = Client()
        self.chroma_client = chromadb.PersistentClient(
            path=kwargs.get("persist_directory"),
            settings=Settings(allow_reset=True, is_persistent=True),
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE,
        )

        # LLM options
        self.options: Optional[Options] = kwargs.get("options")

        # Dictionary to store all collections
        self.collections: Dict[str, RAGCollection] = {}

        # Dictionary to store document references
        self.document_refs: Dict[str, DocumentReference] = {}

        self._load_existing_collections_and_refs()
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

    def get_init_messages(
        self,
        user_query: str,
        collection_names: List[str] = None,
        selected_ids: List[str] = None,
    ) -> List[Dict[str, str]]:
        """Generates init messages for RAG chat."""

        if collection_names:
            collections_to_query = [
                self.collections[name]
                for name in collection_names
                if name in self.collections
            ]
        else:
            collections_to_query = list(self.collections.values())

        def summarize_messages(messages):
            return self.ollama_client.chat(
                model=self.model_id,
                messages=messages,
                options=self.options,
            )["message"]["content"]

        context_text = self.context_manager.get_context_text(
            user_query=user_query,
            summarize_prompt=self.summarize_prompt,
            collections=collections_to_query,
            selected_ids=selected_ids,
            chat_callback=summarize_messages,
        )

        # Construct messages with clear sections and instructions
        messages = [
            {"role": "system", "content": self.context_prompt},
            {
                "role": "user",
                "content": f"Please answer based on the following context and query:\n[CONTEXT]\n{context_text}\n[QUERY]\n{user_query}",
            },
        ]

        return messages

    def forward(
        self,
        user_query: str,
        collection_names: List[str] = None,
        selected_ids: List[str] = None,
    ) -> Iterator[str]:
        """Generate a response using RAG with filtered and optimized context."""

        messages = self.get_init_messages(
            user_query=user_query,
            collection_names=collection_names,
            selected_ids=selected_ids,
        )

        # Generate response token by token
        stream = self.ollama_client.chat(
            model=self.model_id,
            messages=messages,
            stream=True,
            options=self.options,
        )

        for chunk in stream:
            yield chunk["message"]["content"]
