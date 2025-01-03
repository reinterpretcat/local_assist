import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings

from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader
import os
from typing import Iterator, Optional

from .common import BaseModel
from ollama import Client, ResponseError, Options


class RAG(BaseModel):
    """
    A class for Retrival Augument Generation using the ollama library.

    This class inherits from the BaseModel class and provides methods for checking if a model exists,
    and generating text from user input using the specified LLM.

    Args:
        **kwargs: Keyword arguments for initializing the LLM/RAG

    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        persist_directory = kwargs.get("persist_directory")

        self.ollama_client = Client()
        self.chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(),
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE,
        )
        self.collection = self.chroma_client.get_or_create_collection(name="documents")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")  # Embedding model

    def add_pdf(self, file_path):
        """Parse and add content from a PDF file."""
        reader = PdfReader(file_path)
        chunks = [page.extract_text() for page in reader.pages if page.extract_text()]
        self._add_to_collection(file_path, chunks)

    def add_text(self, file_path):
        """Parse and add content from a plain text file."""
        with open(file_path, "r", encoding="utf-8") as f:
            chunks = f.read().split("\n\n")  # Split into paragraphs
        self._add_to_collection(file_path, chunks)

    def add_markdown(self, file_path):
        """Parse and add content from a Markdown file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        chunks = content.split("\n\n")  # Split into paragraphs or sections
        self._add_to_collection(file_path, chunks)

    def _add_to_collection(self, file_path, chunks):
        """Add chunks to the ChromaDB collection with unique IDs, avoiding duplicates."""
        embeddings = self.model.encode(chunks, convert_to_numpy=True)
        base_id = os.path.basename(file_path).replace(
            " ", "_"
        )  # Clean file name for ID base

        # Fetch existing metadata to check for duplicates
        existing_metadatas = self.collection.get(include=["metadatas"])["metadatas"]
        existing_ids = {meta.get("id") for meta in existing_metadatas}

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            unique_id = f"{base_id}_{idx}"

            # Add only if the ID is not already in the collection
            if unique_id not in existing_ids:
                self.collection.add(
                    ids=[unique_id],
                    documents=[chunk],
                    embeddings=[embedding.tolist()],
                    metadatas=[{"source": file_path, "id": unique_id}],
                )

    def retrieve_and_limit_context(self, query, top_k=5, token_limit=1500):
        """
        Retrieve relevant document chunks and ensure the combined token count
        fits within the limit for the context window.

        Args:
            query (str): The user's query.
            top_k (int): Number of top chunks to retrieve.
            token_limit (int): Maximum tokens to allow for the context.

        Returns:
            list[str]: List of selected chunks fitting within the token limit.
        """
        # Step 1: Retrieve relevant chunks
        query_embedding = self.model.encode([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()], n_results=top_k
        )
        chunks = results["documents"][0]

        # Step 2: Fit chunks within the token limit
        selected_chunks = []
        total_tokens = 0

        for chunk in chunks:
            chunk_tokens = len(chunk.split())  # Approximation: 1 word ≈ 1 token
            if total_tokens + chunk_tokens <= token_limit:
                selected_chunks.append(chunk)
                total_tokens += chunk_tokens
            else:
                break

        return selected_chunks

    def summarize_chunks(self, chunks, token_limit=1500):
        """
        Summarize the retrieved chunks to reduce their token count.

        Args:
            chunks (list[str]): List of retrieved document chunks.
            token_limit (int): Target token limit for the summarized content.

        Returns:
            str: Summarized text fitting within the token limit.
        """
        prompt = "Summarize the following information concisely:\n\n" + "\n\n".join(
            chunks
        )

        # Use Ollama to summarize the chunks
        response = self.ollama_client.chat([{"role": "user", "content": prompt}])
        summary = response["content"]

        # Ensure the summary fits within the token limit
        if len(summary.split()) > token_limit:
            summary = " ".join(summary.split()[:token_limit]) + "..."

        return summary

    def forward(self, user_query) -> Iterator[str]:
        """
        Generate a response using RAG with context window management.

        Args:
            user_query (str): The user's query.

        Returns:
            str: Generated response from Ollama.
        """
        # Step 1: Retrieve relevant chunks
        context_chunks = self.retrieve_and_limit_context(
            user_query, top_k=5, token_limit=1500
        )

        # Step 2: Summarize chunks if necessary
        if sum(len(chunk.split()) for chunk in context_chunks) > 1500:
            context_chunks = [self.summarize_chunks(context_chunks)]

        # Step 3: Construct the prompt
        prompt = (
            f"[CONTEXT]\n{'\n'.join(context_chunks)}\n\n"
            f"[QUERY]\n{user_query}\n\n"
            f"[INSTRUCTION]\nAnswer based on the provided context."
        )

        # Step 4: Generate response
        stream = self.ollama_client.chat(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        for chunk in stream:
            yield chunk["message"]["content"]
