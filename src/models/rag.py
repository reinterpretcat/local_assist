import chromadb
import datetime
from typing import Any, List, Optional, Dict
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

from .common import BaseModel


class TextCleaner(TransformComponent):
    """Cleans text by removing unwanted characters and formatting."""

    def __call__(self, nodes: List[BaseNode], **kwargs) -> List[BaseNode]:
        for node in nodes:
            content = node.get_content()
            content = content.replace("\t", " ").replace(" \n", " ")
            node.set_content(content)
        return nodes


class RAG(BaseModel):
    """Manages RAG on document collections using ChromaDB."""

    DEFAULT_PARAMS = {
        "persist_dir": "./chroma_db",
        "embed_model_name": "all-MiniLM-L6-v2",
        "model": "llama3:latest",
        "temperature": 0.0,
        "chunk_size": 512,
        "chunk_overlap": 64,
        "similarity_top_k": 2,
        # Check https://docs.llamaindex.ai/en/stable/module_guides/loading/simpledirectoryreader/
        "supported_extensions": [".csv", ".docx", ".epub", ".md", ".pdf", ".txt"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Merge default params with user-provided params
        params = {**self.DEFAULT_PARAMS, **kwargs}

        self.persist_dir = Path(params["persist_dir"])
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.embed_model_name = params["embed_model_name"]
        self.llm_model = params["model"]
        self.temperature = params["temperature"]
        self.chunk_size = params["chunk_size"]
        self.chunk_overlap = params["chunk_overlap"]
        self.similarity_top_k = params["similarity_top_k"]
        self.supported_extensions = params["supported_extensions"]

        self.embed_model = HuggingFaceEmbedding(model_name=self.embed_model_name)
        self.llm = Ollama(
            model=self.llm_model,
            temperature=self.temperature,
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
            collection = self.get_collection(collection_name)
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
        if path.is_file() and path.suffix in self.supported_extensions:
            reader = SimpleDirectoryReader(input_files=[str(path)])
        else:
            reader = SimpleDirectoryReader(
                input_dir=str(path),
                required_exts=self.supported_extensions,
                input_files=file_filter,
            )

        documents = reader.load_data()
        pipeline = self._get_or_create_pipeline(collection_name)
        nodes = pipeline.run(documents=documents)

        metadata = [
            {
                "id": str(i),
                "source": str(path),
                "chunk_size": self.chunk_size,
                "created_at": datetime.datetime.now().isoformat(),
            }
            for i, _ in enumerate(nodes)
        ]

        collection = self.get_collection(collection_name)
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

    def delete_document(self, collection_name: str, source_path: str) -> None:
        """
        Delete a document and all its chunks from a collection.

        Args:
            collection_name (str): Name of the collection
            source_path (str): Source path of the document to delete
        """
        collection = self.get_collection(collection_name)
        # Get all document chunks with matching source path
        result = collection.get(
            where={"source": str(source_path)},
            include=["documents", "metadatas", "ids"],
        )

        if result["ids"]:
            # Delete all chunks associated with the document
            collection.delete(ids=result["ids"])

    def rename_collection(self, old_name: str, new_name: str) -> None:
        """
        Rename a collection while preserving its contents.

        Args:
            old_name (str): Current name of the collection
            new_name (str): New name for the collection
        """
        # Get the old collection
        old_collection = self.get_collection(old_name)

        # Get all documents from old collection
        docs = old_collection.get()

        # Create new collection
        new_collection = self.get_collection(new_name)

        # Copy documents to new collection if there are any
        if docs["ids"]:
            new_collection.add(
                documents=docs["documents"],
                metadatas=docs["metadatas"],
                ids=docs["ids"],
            )

        # Delete old collection
        self.delete_collection(old_name)

    def get_document_info(self, collection_name: str, source_path: str) -> Dict:
        """
        Get information about a specific document in a collection.

        Args:
            collection_name (str): Name of the collection
            source_path (str): Source path of the document

        Returns:
            Dict: Document information including chunk count and metadata
        """
        collection = self.get_collection(collection_name)
        result = collection.get(
            where={"source": str(source_path)}, include=["metadatas"]
        )

        if result["metadatas"]:
            return {
                "chunk_count": len(result["metadatas"]),
                "source": source_path,
                "created_at": result["metadatas"][0].get("created_at"),
                "chunk_size": result["metadatas"][0].get("chunk_size"),
            }
        return None

    def _get_or_create_pipeline(self, collection_name: str) -> IngestionPipeline:
        """
        Get or create an ingestion pipeline for a collection.

        Args:
            collection_name (str): Name of the collection

        Returns:
            IngestionPipeline: The pipeline for document processing
        """
        if collection_name not in self._pipelines:
            collection = self.get_collection(collection_name)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            text_splitter = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            self._pipelines[collection_name] = IngestionPipeline(
                transformations=[TextCleaner(), text_splitter],
                vector_store=vector_store,
            )
        return self._pipelines[collection_name]

    def get_collection(self, name: str):
        """
        Get or create a ChromaDB collection.

        Args:
            name (str): Name of the collection

        Returns:
            chromadb.Collection: The ChromaDB collection
        """
        return self.chroma_client.get_or_create_collection(name)

    def load_collection(self, collection_name: str) -> None:
        """
        Load an existing collection into memory for querying.

        Args:
            collection_name (str): Name of the collection to load
        """
        collection = self.get_collection(collection_name)
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
            metadata_filters (Optional[MetadataFilters]): Metadata filtering criteria

        Returns:
            List[str]: Relevant context content
        """
        collection = self.get_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        index = VectorStoreIndex.from_vector_store(
            vector_store, embed_model=self.embed_model
        )
        retriever = index.as_retriever(
            similarity_top_k=self.similarity_top_k, filters=metadata_filters
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
            metadata_filters (Optional[MetadataFilters]): Metadata filtering criteria

        Returns:
            str: Generated answer
        """
        collection = self.get_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=self.embed_model,
        )
        query_engine = index.as_query_engine(
            similarity_top_k=self.similarity_top_k,
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

    def forward(self, model_input):
        print("not implemented")
        return super().forward(model_input)
