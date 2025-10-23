"""Vector database implementation using ChromaDB."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from .chunker import TextChunker

logger = logging.getLogger(__name__)


class VectorDB:
    """Vector database wrapper for memov using ChromaDB with lightweight embedding options."""

    def __init__(
        self,
        persist_directory: Path,
        collection_name: str = "memov_memories",
        chunk_size: int = 768,
        embedding_backend: str = "default",
        embedding_model: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialize the vector database with flexible embedding backends.

        Args:
            persist_directory: Directory to persist the ChromaDB database
            collection_name: Name of the ChromaDB collection
            chunk_size: Maximum size of text chunks (default: 768)
            embedding_backend: Backend to use:
                - "default" (recommended): ChromaDB's built-in embedding (~50MB)
                - "fastembed": FastEmbed with ONNX Runtime (~30MB)
                - "openai": OpenAI API (requires API key, <5MB)
                - "sentence-transformers": Original implementation (~1.5GB)
            embedding_model: Optional model name override
            openai_api_key: OpenAI API key (required if backend="openai")
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.chunker = TextChunker(chunk_size=chunk_size)
        self.embedding_backend = embedding_backend

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )

        # Initialize embedding function based on backend
        self.embedding_function = self._create_embedding_function(
            embedding_backend, embedding_model, openai_api_key
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Memov prompt and plan storage"},
        )

        logger.info(
            f"VectorDB initialized at {self.persist_directory} "
            f"with collection '{self.collection_name}' using '{embedding_backend}' backend"
        )

    def _create_embedding_function(
        self,
        backend: str,
        model_name: Optional[str],
        openai_api_key: Optional[str],
    ):
        """
        Create appropriate embedding function based on backend choice.

        Args:
            backend: Embedding backend type
            model_name: Optional model name override
            openai_api_key: OpenAI API key if using OpenAI backend

        Returns:
            Embedding function compatible with ChromaDB
        """
        if backend == "default":
            # Use ChromaDB's built-in default embedding (lightweight, no extra deps)
            logger.info("Using ChromaDB default embedding (lightweight, ~50MB)")
            return embedding_functions.DefaultEmbeddingFunction()

        elif backend == "fastembed":
            # Use FastEmbed with ONNX Runtime (lightweight alternative)
            try:
                from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

                logger.info("Using FastEmbed ONNX embedding (~30MB)")
                return ONNXMiniLM_L6_V2()
            except ImportError:
                logger.warning(
                    "FastEmbed not available, falling back to default. "
                    "Install with: pip install chromadb[onnx]"
                )
                return embedding_functions.DefaultEmbeddingFunction()

        elif backend == "openai":
            # Use OpenAI API (requires API key, very lightweight client)
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                    "or pass openai_api_key parameter"
                )

            logger.info("Using OpenAI embedding API (requires API key)")
            model = model_name or "text-embedding-3-small"
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key, model_name=model
            )

        elif backend == "sentence-transformers":
            # Original implementation (heavy, ~1.5GB)
            try:
                logger.warning(
                    "Using sentence-transformers backend (~1.5GB). "
                    "Consider using 'default' or 'fastembed' for lighter installation."
                )
                model = model_name or "all-MiniLM-L6-v2"
                return embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=model
                )
            except ImportError:
                logger.error(
                    "sentence-transformers not available. "
                    "Install with: pip install sentence-transformers"
                )
                raise

        else:
            raise ValueError(
                f"Unknown embedding backend: {backend}. "
                f"Choose from: default, fastembed, openai, sentence-transformers"
            )

    def insert(
        self,
        text: str,
        metadata: Dict[str, Any],
        doc_id: Optional[str] = None,
    ) -> List[str]:
        """
        Insert text into the vector database with automatic chunking.

        Args:
            text: The text to insert (will be automatically chunked)
            metadata: Metadata dictionary containing:
                - operation_type: track|snap|rename|remove
                - source: user|ai
                - files: List of files (optional)
                - commit_hash: Git commit hash
                - parent_hash: Parent commit hash (optional)
                - timestamp: ISO format timestamp (optional)
            doc_id: Optional base document ID (chunks will be suffixed with _0, _1, etc.)

        Returns:
            List of inserted document IDs
        """
        # Chunk the text with metadata
        chunks_with_metadata = self.chunker.chunk_with_metadata(text, metadata)

        # Prepare batch data
        ids = []
        documents = []
        metadatas = []

        for idx, (chunk_text, chunk_metadata) in enumerate(chunks_with_metadata):
            # Generate ID
            if doc_id:
                chunk_id = f"{doc_id}_chunk_{idx}"
            else:
                chunk_id = f"{metadata.get('commit_hash', 'unknown')}_{idx}"

            ids.append(chunk_id)
            documents.append(chunk_text)
            metadatas.append(chunk_metadata)

        # Insert into ChromaDB
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        logger.debug(f"Inserted {len(ids)} chunks into VectorDB")
        return ids

    def search(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar texts in the vector database.

        Args:
            query_text: The query text to search for
            n_results: Number of results to return (default: 5)
            where: Optional filter conditions (e.g., {"operation_type": "track"})

        Returns:
            List of search results, each containing:
                - id: Document ID
                - text: The chunk text
                - metadata: Associated metadata
                - distance: Similarity distance (lower is more similar)
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
        )

        # Parse results
        parsed_results = []
        if results["ids"] and results["ids"][0]:
            for idx in range(len(results["ids"][0])):
                parsed_results.append(
                    {
                        "id": results["ids"][0][idx],
                        "text": results["documents"][0][idx],
                        "metadata": results["metadatas"][0][idx],
                        "distance": results["distances"][0][idx],
                    }
                )

        return parsed_results

    def get_by_commit(self, commit_hash: str) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks associated with a specific commit.

        Args:
            commit_hash: The commit hash to search for

        Returns:
            List of documents with their metadata
        """
        results = self.collection.get(where={"commit_hash": commit_hash})

        parsed_results = []
        if results["ids"]:
            for idx in range(len(results["ids"])):
                parsed_results.append(
                    {
                        "id": results["ids"][idx],
                        "text": results["documents"][idx],
                        "metadata": results["metadatas"][idx],
                    }
                )

        return parsed_results

    def delete_by_commit(self, commit_hash: str) -> None:
        """
        Delete all chunks associated with a specific commit.

        Args:
            commit_hash: The commit hash to delete
        """
        self.collection.delete(where={"commit_hash": commit_hash})
        logger.debug(f"Deleted all chunks for commit {commit_hash}")

    def update_metadata(self, doc_id: str, new_metadata: Dict[str, Any]) -> None:
        """
        Update metadata for a specific document.

        Args:
            doc_id: The document ID to update
            new_metadata: New metadata to set
        """
        self.collection.update(ids=[doc_id], metadatas=[new_metadata])
        logger.debug(f"Updated metadata for document {doc_id}")

    def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all documents from the collection.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of all documents with their metadata
        """
        results = self.collection.get(limit=limit)

        parsed_results = []
        if results["ids"]:
            for idx in range(len(results["ids"])):
                parsed_results.append(
                    {
                        "id": results["ids"][idx],
                        "text": results["documents"][idx],
                        "metadata": results["metadatas"][idx],
                    }
                )

        return parsed_results

    def find_similar_prompts(
        self, query_prompt: str, n_results: int = 5, operation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find prompts similar to the query prompt.

        Args:
            query_prompt: The prompt to search for
            n_results: Number of similar prompts to return
            operation_type: Optional filter by operation type (track, snap, etc.)

        Returns:
            List of similar prompts with their commit hashes
        """
        where = None
        if operation_type:
            where = {"operation_type": operation_type}

        return self.search(query_text=query_prompt, n_results=n_results, where=where)

    def find_commits_by_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Find commits that involve specific files.

        Args:
            file_paths: List of file paths to search for

        Returns:
            List of commits involving these files
        """
        # ChromaDB doesn't support array contains queries directly,
        # so we need to query for each file and combine results
        all_results = []
        seen_commit_hashes = set()

        for file_path in file_paths:
            # Get all documents and filter in Python
            all_docs = self.get_all()
            for doc in all_docs:
                metadata = doc.get("metadata", {})
                # Files are stored as comma-separated string
                files_str = metadata.get("files", "")
                files = [f.strip() for f in files_str.split(",") if f.strip()]
                commit_hash = metadata.get("commit_hash")

                if file_path in files and commit_hash not in seen_commit_hashes:
                    all_results.append(doc)
                    seen_commit_hashes.add(commit_hash)

        return all_results

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.

        Returns:
            Dictionary containing collection statistics
        """
        count = self.collection.count()
        return {
            "name": self.collection_name,
            "count": count,
            "persist_directory": str(self.persist_directory),
        }

    def reset(self) -> None:
        """
        Delete and recreate the collection (removes all data).
        """
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Memov prompt and plan storage"},
        )
        logger.warning(f"Reset collection '{self.collection_name}' - all data deleted")
