import chromadb
import datetime
from dataclasses import dataclass
from typing import Any, List, Optional
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import BaseNode, TransformComponent
from llama_index.core.text_splitter import SentenceSplitter
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.vector_stores import MetadataFilters
from llama_index.core import Settings


@dataclass
class RAGParameters:
    """Configuration parameters for the RAG system."""

    # Embedding model parameters
    embed_model_name: str = "all-MiniLM-L6-v2"

    # LLM parameters
    llm_model: str = "llama3:latest"
    temperature: float = 0.0

    # Text splitting parameters
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Retrieval parameters
    similarity_top_k: int = 2

    # Supported file types
    supported_extensions: List[str] = None

    def __post_init__(self):
        if self.supported_extensions is None:
            # Taken from https://docs.llamaindex.ai/en/stable/module_guides/loading/simpledirectoryreader/
            self.supported_extensions = [
                ".csv",
                ".docx",
                ".epub",
                ".md ",
                ".pdf",
                ".ppt",
                ".pptm",
                ".pptx",
            ]


class TextCleaner(TransformComponent):
    """Cleans text by removing unwanted characters and formatting."""

    def __call__(self, nodes: List[BaseNode], **kwargs) -> List[BaseNode]:
        for node in nodes:
            content = node.get_content()
            content = content.replace("\t", " ").replace(" \n", " ")
            node.set_content(content)
        return nodes


class DocumentManager:
    """Manages document collections and operations using ChromaDB."""

    def __init__(self, persist_dir: str, params: Optional[RAGParameters] = None):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.params = params or RAGParameters()
        self.embed_model = HuggingFaceEmbedding(model_name=self.params.embed_model_name)
        self.llm = Ollama(
            model=self.params.llm_model,
            temperature=self.params.temperature,
            timeout=120,  # Timeout in seconds
        )
        self.chroma_client = chromadb.PersistentClient(path=str(self.persist_dir))

        Settings.embed_model = self.embed_model
        Settings.llm = self.llm

        self._pipelines = {}

    def list_collections(self) -> List[dict]:
        """
        List all available document collections with their basic info.

        Returns:
            List[dict]: List of collection information dictionaries
        """
        collections = []
        for name in self.chroma_client.list_collections():
            info = self.get_collection_info(name)
            if info:
                collections.append(info)
        return collections

    def get_collection_info(self, collection_name: str) -> Optional[dict]:
        """
        Get detailed information about a specific collection.

        Args:
            collection_name (str): Name of the collection

        Returns:
            dict: Collection information including document count and metadata summary
        """
        try:
            collection = self._get_collection(collection_name)
            metadata_result = collection.get(include=["metadatas"])
            metadatas = metadata_result.get("metadatas", [])

            unique_sources = {meta.get("source") for meta in metadatas if meta}
            return {
                "name": collection_name,
                "document_count": collection.count(),
                "unique_sources": list(unique_sources),
            }
        except Exception as e:
            print(f"Error fetching collection '{collection_name}': {e}")
            return None

    def add_documents(
        self, path: str, collection_name: str, file_filter: Optional[List[str]] = None
    ):
        """
        Add documents from a file or directory into a specified collection.

        Args:
            path (str): Path to directory or specific file
            collection_name (str): Name for the document collection
            file_filter (Optional[List[str]]): List of specific filenames to load from directory
        """
        path = Path(path)
        if path.is_file() and path.suffix in self.params.supported_extensions:
            reader = SimpleDirectoryReader(input_files=[str(path)])
        else:
            reader = SimpleDirectoryReader(
                input_dir=str(path),
                required_exts=self.params.supported_extensions,
                input_files=file_filter,
            )

        documents = reader.load_data()
        pipeline = self._get_or_create_pipeline(collection_name)
        nodes = pipeline.run(documents=documents)

        metadata = [
            {
                "id": str(i),
                "source": str(path),
                "chunk_size": self.params.chunk_size,
                "created_at": datetime.datetime.now().isoformat(),
            }
            for i, _ in enumerate(nodes)
        ]

        collection = self._get_collection(collection_name)
        for node, meta in zip(nodes, metadata):
            node.metadata.update(meta)
            collection.upsert(
                documents=[node.get_content()], metadatas=[meta], ids=[meta["id"]]
            )

    def add_document(self, file_path: str, collection_name: str) -> None:
        """
        Add a single document to a collection.

        Args:
            file_path (str): Path to the document file
            collection_name (str): Name of the collection to add the document to
        """
        self.add_documents(file_path, collection_name)

    def _get_or_create_pipeline(self, collection_name: str) -> IngestionPipeline:
        if collection_name not in self._pipelines:
            collection = self._get_collection(collection_name)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            text_splitter = SentenceSplitter(
                chunk_size=self.params.chunk_size,
                chunk_overlap=self.params.chunk_overlap,
            )
            self._pipelines[collection_name] = IngestionPipeline(
                transformations=[TextCleaner(), text_splitter],
                vector_store=vector_store,
            )
        return self._pipelines[collection_name]

    def _get_collection(self, name: str):
        return self.chroma_client.get_or_create_collection(name)

    def load_collection(self, collection_name: str) -> None:
        """
        Load an existing collection into memory for querying.

        Args:
            collection_name (str): Name of the collection to load
        """
        collection = self._get_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        self._pipelines[collection_name] = IngestionPipeline(vector_store=vector_store)

    def retrieve_context(
        self,
        query: str,
        collection_name: str,
        metadata_filters: Optional[MetadataFilters] = None,
    ) -> List[str]:
        """
        Retrieve relevant context for a query from a specific collection.

        Args:
            query (str): Query string
            collection_name (str): Name of the collection to search
            metadata_filter (Optional[MetadataFilters]): Dictionary specifying metadata filtering criteria

        Returns:
            List[str]: Relevant context content
        """
        collection = self._get_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        index = VectorStoreIndex.from_vector_store(
            vector_store, embed_model=self.embed_model
        )
        retriever = index.as_retriever(
            similarity_top_k=self.params.similarity_top_k, filters=metadata_filters
        )
        return [node.get_content() for node in retriever.retrieve(query)]

    def answer_question(
        self,
        question: str,
        collection_name: str,
        metadata_filters: Optional[MetadataFilters] = None,
    ) -> str:
        """
        Generate an answer to a question using a specific collection.

        Args:
            question (str): Question to answer
            collection_name (str): Name of the collection to use
            metadata_filter (Optional[MetadataFilters]): Dictionary specifying metadata filtering criteria

        Returns:
            str: Generated answer
        """
        collection = self._get_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=self.embed_model,
        )
        query_engine = index.as_query_engine(
            similarity_top_k=self.params.similarity_top_k,
            filters=metadata_filters,
        )

        context = [node.get_content() for node in query_engine.retrieve(question)]
        context_string = " ".join(context)

        prompt = f"""
Context: {context_string}

Instructions:
1. Answer the question using only the provided context.
2. If the context is insufficient, say "I cannot answer this question based on the provided information."
3. Be concise and accurate.

Question: {question}

Answer:
        """
        return self.llm.complete(prompt).text

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection and its associated data.

        Args:
            collection_name (str): Name of the collection to delete
        """
        self.chroma_client.delete_collection(collection_name)
        if collection_name in self._pipelines:
            del self._pipelines[collection_name]
