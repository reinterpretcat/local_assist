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


class ImprovedContextManager:
    def __init__(self, **kwargs):

        self.token_limit = int(kwargs.get("token_limit"))
        self.min_relevance = float(kwargs.get("min_relevance"))
        self.top_k = int(kwargs.get("top_k"))

        # Common quote marks across different languages/styles
        self.quote_pairs = [
            ('"', '"'),  # English double quotes
            ("'", "'"),  # English single quotes
            ("«", "»"),  # French/Russian quotation marks
            ("„", '"'),  # German quotation marks
            ('"', '"'),  # Curved double quotes
            (""", """),  # Curved single quotes
            ("「", "」"),  # Japanese/Chinese quotes
            ("《", "》"),  # Chinese/Korean quotes
            ("‹", "›"),  # Single angle quotes
            ("（", "）"),  # Full-width parentheses
        ]

    def retrieve_and_limit_context(
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

        selected_text = self._limit_context(all_chunks)
        return selected_text

    def summarize_chunks(
        self, summarize_prompt, chunks: List[str], chat_callback
    ) -> str:
        """
        Language-independent chunk summarization with context preservation.
        """
        # Combine related chunks before summarization
        grouped_chunks = self._group_related_chunks(chunks)

        messages = [
            {"role": "system", "content": summarize_prompt},
            {
                "role": "user",
                "content": f"Summarize while preserving context, dialogue, and language style:\n\n{'\n\n'.join(grouped_chunks)}",
            },
        ]

        response = chat_callback(messages)

        # Post-process the summary to ensure quality
        summary = self._post_process_summary(response["content"])

        return summary

    def _limit_context(self, all_chunks):
        """Group chunks by source and sort them while respecting the token limit."""
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
                if selected_total_tokens + chunk["tokens"] <= self.token_limit:
                    selected_text.append(chunk["text"])
                    selected_total_tokens += chunk["tokens"]
                else:
                    break

        return selected_text

    def _group_related_chunks(self, chunks: List[str]) -> List[str]:
        """
        Group related chunks based on narrative continuity, independent of language.
        """
        grouped = []
        current_group = []

        for chunk in chunks:
            # Check if chunk is related to current group
            if not current_group or self._are_chunks_related(current_group[-1], chunk):
                current_group.append(chunk)
            else:
                # Start new group if not related
                if current_group:
                    grouped.append("\n".join(current_group))
                current_group = [chunk]

        # Add final group
        if current_group:
            grouped.append("\n".join(current_group))

        return grouped

    def _are_chunks_related(self, chunk1: str, chunk2: str) -> bool:
        """
        Determine if two chunks are narratively related, using language-agnostic markers.
        """
        # Check for dialogue using any quote style
        has_dialogue = self._has_dialogue(chunk1) and self._has_dialogue(chunk2)

        # Check for scene continuity
        same_scene = self._check_same_scene(chunk1, chunk2)

        return has_dialogue or same_scene

    def _has_dialogue(self, text: str) -> bool:
        """
        Check for presence of dialogue using various quote styles.
        """
        return any(
            opening in text or closing in text for opening, closing in self.quote_pairs
        )

    def _check_same_scene(self, chunk1: str, chunk2: str) -> bool:
        """
        Check if chunks are from the same scene using structural analysis.
        """
        # Look for paragraph breaks
        if chunk2.startswith("\n\n") or chunk2.startswith("\r\n\r\n"):
            return False

        # Check for speaker changes in dialogue
        if self._has_dialogue(chunk2):
            speakers1 = self._extract_speakers(chunk1)
            speakers2 = self._extract_speakers(chunk2)
            return bool(speakers1.intersection(speakers2))

        return True

    def _extract_speakers(self, text: str) -> Set[str]:
        """
        Extract potential speaker names from dialogue, using general patterns.
        """
        speakers = set()

        # Look for common dialogue attribution patterns
        for opening, closing in self.quote_pairs:
            # Split by quote marks
            parts = text.split(opening)
            for part in parts[1:]:  # Skip first part (before any quotes)
                if closing in part:
                    # Look for words before/after quotes that might be speaker attribution
                    context = part.split(closing)[1].strip()
                    # Extract word sequences that might be names/speakers
                    words = context.split()[:2]  # Take up to 2 words after quote
                    if words:
                        speakers.add(" ".join(words))

        return speakers

    def _post_process_summary(self, summary: str) -> str:
        """
        Clean up and improve the summary output while preserving language-specific formatting.
        """
        # Preserve original quote styles
        processed_summary = summary

        # Split into lines while preserving empty lines
        lines = processed_summary.split("\n")
        processed_lines = []

        current_quote_style = None
        for line in lines:
            # Preserve empty lines
            if not line.strip():
                processed_lines.append(line)
                continue

            # Detect quote style being used in this line
            for opening, closing in self.quote_pairs:
                if opening in line or closing in line:
                    current_quote_style = (opening, closing)
                    break

            # Ensure dialogue starts on new lines
            if current_quote_style and current_quote_style[0] in line:
                opening, closing = current_quote_style
                if not line.strip().startswith(opening):
                    dialogue_parts = line.split(opening)
                    processed_lines.extend(
                        [
                            dialogue_parts[0].strip(),
                            opening + opening.join(dialogue_parts[1:]),
                        ]
                    )
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)

        processed_summary = "\n".join(processed_lines)

        # Truncate if over token limit while preserving quote pairs
        if len(processed_summary.split()) > self.token_limit:
            words = processed_summary.split()
            truncated = " ".join(words[: self.token_limit - 1])

            # Balance any unmatched quotes
            for opening, closing in self.quote_pairs:
                if truncated.count(opening) > truncated.count(closing):
                    truncated += closing

            truncated += "..."
            return truncated

        return processed_summary


class RAG(BaseModel):
    def __init__(self, **kwargs) -> None:
        """A class for Retrieval Augmented Generation using the ollama library."""
        super().__init__(**kwargs)

        self.summarize_prompt = kwargs.get("summarize_prompt")
        self.context_prompt = kwargs.get("context_prompt")

        self.context_manager = ImprovedContextManager(**kwargs)

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

        context_chunks = self.context_manager.retrieve_and_limit_context(
            query=user_query,
            collections=collections_to_query,
            selected_ids=selected_ids,
        )

        def summarize_messages(messages):
            return self.ollama_client.chat(
                model=self.model_id,
                messages=messages,
                options=self.options,
            )

        # Summarize chunks if the combined length exceeds token_limit
        total_tokens = sum(len(chunk.split()) for chunk in context_chunks)
        if total_tokens > self.context_manager.token_limit:
            context_chunks = [
                self.context_manager.summarize_chunks(
                    self.summarize_prompt,
                    context_chunks,
                    chat_callback=summarize_messages,
                )
            ]

        context_text = "\n".join(context_chunks)

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
