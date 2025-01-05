from dataclasses import dataclass
from collections import defaultdict
from typing import List, Iterator, Optional, Dict, Set, Any
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader
import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
from ollama import Client, Options
import os
from pathlib import Path
from .common import BaseModel
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


@dataclass
class ChunkInfo:
    text: str
    tokens: int
    relevance: float
    metadata: Dict[str, Any]
    source: str
    source_position: int


class ContextManager:
    def __init__(self, **kwargs):
        self.token_limit = int(kwargs.get("token_limit", 4000))
        self.min_relevance = float(kwargs.get("min_relevance", 0.7))
        self.top_k = int(kwargs.get("top_k", 5))

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count using word-based approximation."""
        return int(len(text.split()) * 1.3)

    def get_context_text(
        self,
        user_query: str,
        summarize_prompt: str,
        collections: List[RAGCollection],
        selected_ids: Dict[str, List[str]],
        chat_callback,
    ) -> str:
        # Retrieve and group relevant chunks
        grouped_chunks = self._retrieve_and_limit_context(
            query=user_query,
            collections=collections,
            selected_ids=selected_ids,
        )

        if not grouped_chunks:
            return "No relevant context found."

        # Calculate token limit per chunk based on number of chunks
        total_chunks = sum(len(chunks) for chunks in grouped_chunks.values())
        # Reserve 20% of tokens for prompts and overhead
        available_tokens = int(self.token_limit * 0.8)
        chunk_token_limit = (
            available_tokens // total_chunks if total_chunks > 0 else available_tokens
        )

        context_text_blocks = []
        accumulated_summary = ""

        # Process chunks source by source
        for group_idx, (source, source_chunks) in enumerate(grouped_chunks.items()):
            print_system_message(
                f"process group {group_idx} from {len(grouped_chunks.items())}"
            )

            source_summaries = []
            for chunk_idx, chunk in enumerate(source_chunks):
                print_system_message(
                    f"process chunk {chunk_idx} from {len(source_chunks)}"
                )

                if not isinstance(chunk.text, str) or not chunk.text.strip():
                    continue

                # TODO can use  source, chunk.metadata to keep a reference to document

                # Summarize the chunk
                summary = self._summarize_chunks(
                    summarize_prompt=summarize_prompt,
                    context=accumulated_summary,
                    chunk=chunk.text,  # Make sure we're passing the actual text content
                    chunk_token_limit=chunk_token_limit,
                    chat_callback=chat_callback,
                )

                if summary:
                    source_summaries.append(summary)
                    # Update accumulated summary and context messages
                    accumulated_summary = self._update_accumulated_summary(
                        accumulated_summary, summary
                    )

            if source_summaries:
                # Combine summaries for this source
                source_block = self._format_source_block(source, source_summaries)
                context_text_blocks.append(source_block)

        if not context_text_blocks:
            return "No meaningful summaries generated from the context."

        # Final cleanup and structuring
        return self._create_final_context(context_text_blocks)

    def _retrieve_and_limit_context(
        self,
        query: str,
        collections: List[RAGCollection] = None,
        selected_ids: Dict[str, List[str]] = None,
    ) -> Dict[str, List[ChunkInfo]]:
        """Retrieve and filter relevant chunks while preserving their natural order."""
        all_chunks = []

        for collection in collections:
            # Get selected IDs for this collection
            collection_ids = selected_ids.get(collection.name) if selected_ids else None

            # Query the collection
            results = collection.query(query, self.top_k, collection_ids)

            # Process results
            for idx, (chunk, metadata, distance) in enumerate(
                zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ):
                # Calculate relevance score (convert distance to similarity)
                relevance_score = 1 - (distance / 2)

                # Filter by minimum relevance
                if relevance_score >= self.min_relevance:
                    chunk_info = ChunkInfo(
                        text=chunk,
                        tokens=self._estimate_tokens(chunk),
                        relevance=relevance_score,
                        metadata=metadata,
                        source=metadata.get("source", "unknown"),
                        source_position=metadata.get("chunk_index", idx),
                    )
                    all_chunks.append(chunk_info)

        return self._group_chunks(all_chunks)

    def _group_chunks(
        self,
        chunks: List[ChunkInfo],
    ) -> Dict[str, List[ChunkInfo]]:
        """Group chunks by source and merge them if possible while respecting the context_size limit."""

        # Reserve 10% of tokens for prompts and overhead
        available_tokens = int(self.token_limit * 0.9)

        # First group by source
        initial_groups = defaultdict(list)
        for chunk in chunks:
            initial_groups[chunk.source].append(chunk)

        # Sort each group by source_position
        for source in initial_groups:
            initial_groups[source].sort(key=lambda x: x.source_position)

        # Merge chunks within each source group
        final_groups = {}
        for source, source_chunks in initial_groups.items():
            merged_chunks = []
            current_merged = None

            for chunk in source_chunks:
                if current_merged is None:
                    # Start a new merged chunk
                    current_merged = ChunkInfo(
                        text=chunk.text,
                        tokens=chunk.tokens,
                        relevance=chunk.relevance,
                        metadata=chunk.metadata.copy(),
                        source=chunk.source,
                        source_position=chunk.source_position,
                    )
                else:
                    # Check if we can merge with the current chunk
                    combined_tokens = current_merged.tokens + chunk.tokens
                    if combined_tokens <= available_tokens:
                        # Merge chunks
                        current_merged.text = f"{current_merged.text}\n\n{chunk.text}"
                        current_merged.tokens = combined_tokens
                        # Update relevance as weighted average
                        total_tokens = current_merged.tokens
                        current_merged.relevance = (
                            current_merged.relevance * (total_tokens - chunk.tokens)
                            + chunk.relevance * chunk.tokens
                        ) / total_tokens
                        # Update metadata to indicate merged chunk
                        current_merged.metadata.update(
                            {
                                "merged_chunk": True,
                                "original_positions": current_merged.metadata.get(
                                    "original_positions",
                                    [current_merged.source_position],
                                )
                                + [chunk.source_position],
                            }
                        )
                    else:
                        # Add current merged chunk to results and start a new one
                        merged_chunks.append(current_merged)
                        current_merged = ChunkInfo(
                            text=chunk.text,
                            tokens=chunk.tokens,
                            relevance=chunk.relevance,
                            metadata=chunk.metadata.copy(),
                            source=chunk.source,
                            source_position=chunk.source_position,
                        )

            # Add the last merged chunk if exists
            if current_merged is not None:
                merged_chunks.append(current_merged)

            final_groups[source] = merged_chunks

        return dict(final_groups)

    def _summarize_chunks(
        self,
        summarize_prompt: str,
        context: str,
        chunk: str,
        chunk_token_limit: int,
        chat_callback,
    ) -> str:
        """Summarize chunk while considering previous context."""

        # Construct the summarization prompt that includes the chunk content
        chunk_prompt = (
            f"Please provide a summary for a query, if necessary using previous contexts in approximately {chunk_token_limit} words.\n\n"
            f"[CONTEXT]{context}\n"
            f"[QUERY]\n{chunk}"
        )

        # Prepare the messages for the LLM
        messages = [
            {"role": "system", "content": summarize_prompt},
            {"role": "user", "content": chunk_prompt},
        ]

        print(f"{messages=}")

        summary = chat_callback(messages).strip()

        print(f"received: {summary=}")

        # Ensure summary is within token limit
        if self._estimate_tokens(summary) > chunk_token_limit:
            words = summary.split()
            estimated_words_limit = int(chunk_token_limit / 1.3)
            summary = " ".join(words[:estimated_words_limit])

        return summary

    def _update_accumulated_summary(
        self, current_summary: str, new_summary: str
    ) -> str:
        if not current_summary:
            return new_summary

        combined = f"{current_summary}\n\nAdditional context: {new_summary}"
        if self._estimate_tokens(combined) > self.token_limit:
            words = combined.split()
            estimated_words_limit = int(self.token_limit / 1.3)
            combined = " ".join(words[-estimated_words_limit:])
        return combined

    def _format_source_block(self, source: str, summaries: List[str]) -> str:
        formatted = f"\n### Source: {source}\n\n"
        formatted += "\n".join(summaries)
        return formatted

    def _create_final_context(self, context_blocks: List[str]) -> str:
        final_context = "\n\n".join(context_blocks)
        final_context = self._post_process_chunk_summary(final_context)

        if self._estimate_tokens(final_context) > self.token_limit:
            words = final_context.split()
            estimated_words_limit = int(self.token_limit / 1.3)
            final_context = " ".join(words[:estimated_words_limit])

        return final_context

    def _post_process_chunk_summary(self, summary: str) -> str:
        """Clean up and improve the summary structure"""
        # Remove multiple consecutive newlines
        while "\n\n\n" in summary:
            summary = summary.replace("\n\n\n", "\n\n")

        # Ensure consistent heading formatting
        summary = summary.replace("####", "###")

        # Clean up whitespace around headings
        lines = summary.split("\n")
        cleaned_lines = []
        for i, line in enumerate(lines):
            if line.startswith("###"):
                if i > 0:
                    cleaned_lines.append("")
                cleaned_lines.append(line)
                cleaned_lines.append("")
            else:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()


class RAG(BaseModel):
    def __init__(self, **kwargs) -> None:
        """A class for Retrieval Augmented Generation using the ollama library."""
        super().__init__(**kwargs)

        self.summarize_prompt = kwargs.get("summarize_prompt")
        self.context_prompt = kwargs.get("context_prompt")

        self.summary_chunk_prompt = kwargs.get("summary_chunk_prompt")

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
            return (
                self.ollama_client.chat(
                    model=self.model_id,
                    messages=messages,
                    options=self.options,
                )
                .get("message", {})
                .get("content", "")
            )

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
