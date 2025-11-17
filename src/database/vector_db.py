"""FAISS-based vector database for SKU embeddings"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import pickle
import numpy as np
import faiss

logger = logging.getLogger(__name__)


class VectorDatabase:
    """FAISS-based vector database for efficient similarity search"""

    def __init__(
        self,
        dimension: int = 512,
        index_type: str = "IndexFlatL2",
        metric: str = "L2",
        nlist: int = 100,
    ):
        """
        Initialize vector database

        Args:
            dimension: Embedding dimension
            index_type: FAISS index type (IndexFlatL2, IndexIVFFlat, IndexHNSWFlat)
            metric: Distance metric (L2 or IP for inner product)
            nlist: Number of clusters for IVF index
        """
        self.dimension = dimension
        self.index_type = index_type
        self.metric = metric
        self.nlist = nlist

        # Initialize index
        self.index = self._create_index()

        # Metadata storage
        self.metadata: List[Dict[str, Any]] = []

        logger.info(f"Initialized {index_type} with dimension {dimension}")

    def _create_index(self) -> faiss.Index:
        """Create FAISS index based on configuration"""
        if self.index_type == "IndexFlatL2":
            # Brute force L2 distance (most accurate)
            index = faiss.IndexFlatL2(self.dimension)

        elif self.index_type == "IndexFlatIP":
            # Brute force inner product (for cosine similarity)
            index = faiss.IndexFlatIP(self.dimension)

        elif self.index_type == "IndexIVFFlat":
            # IVF with flat quantizer (faster, less accurate)
            quantizer = faiss.IndexFlatL2(self.dimension)
            index = faiss.IndexIVFFlat(
                quantizer,
                self.dimension,
                self.nlist,
                faiss.METRIC_L2
            )

        elif self.index_type == "IndexHNSWFlat":
            # HNSW (fast, good accuracy)
            index = faiss.IndexHNSWFlat(self.dimension, 32)

        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")

        logger.info(f"Created FAISS index: {self.index_type}")
        return index

    def add_embeddings(
        self,
        embeddings: np.ndarray,
        metadata: List[Dict[str, Any]],
    ):
        """
        Add embeddings and metadata to the database

        Args:
            embeddings: Array of embeddings (N, dimension)
            metadata: List of metadata dictionaries for each embedding
        """
        if len(embeddings) != len(metadata):
            raise ValueError("Number of embeddings must match metadata length")

        # Ensure embeddings are float32
        embeddings = embeddings.astype(np.float32)

        # Normalize for cosine similarity (if using IP metric)
        if self.metric == "IP" or "IP" in self.index_type:
            faiss.normalize_L2(embeddings)

        # Train index if needed (IVF requires training)
        if isinstance(self.index, faiss.IndexIVFFlat) and not self.index.is_trained:
            logger.info("Training IVF index...")
            self.index.train(embeddings)

        # Add to index
        self.index.add(embeddings)

        # Add metadata
        self.metadata.extend(metadata)

        logger.info(f"Added {len(embeddings)} embeddings to database. Total: {self.index.ntotal}")

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        return_distances: bool = True,
    ) -> Tuple[List[Dict[str, Any]], Optional[np.ndarray]]:
        """
        Search for k nearest neighbors

        Args:
            query_embedding: Query embedding vector (dimension,)
            k: Number of results to return
            return_distances: Whether to return distances

        Returns:
            Tuple of (metadata_list, distances)
        """
        if self.index.ntotal == 0:
            logger.warning("Database is empty")
            return [], None

        # Ensure query is 2D and float32
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        query_embedding = query_embedding.astype(np.float32)

        # Normalize for cosine similarity
        if self.metric == "IP" or "IP" in self.index_type:
            faiss.normalize_L2(query_embedding)

        # Search
        k = min(k, self.index.ntotal)  # Don't search for more than available
        distances, indices = self.index.search(query_embedding, k)

        # Get metadata for results
        results = []
        for idx in indices[0]:
            if idx >= 0 and idx < len(self.metadata):
                results.append(self.metadata[idx])

        if return_distances:
            # Convert L2 distances to similarity scores (higher is better)
            if "L2" in self.index_type:
                # Convert L2 distance to similarity: similarity = 1 / (1 + distance)
                similarities = 1.0 / (1.0 + distances[0])
            else:
                # For IP, distances are already similarities
                similarities = distances[0]

            return results, similarities
        else:
            return results, None

    def search_batch(
        self,
        query_embeddings: np.ndarray,
        k: int = 5,
    ) -> Tuple[List[List[Dict[str, Any]]], np.ndarray]:
        """
        Batch search for multiple queries

        Args:
            query_embeddings: Query embeddings (N, dimension)
            k: Number of results per query

        Returns:
            Tuple of (list of metadata lists, distances array)
        """
        if self.index.ntotal == 0:
            logger.warning("Database is empty")
            return [[] for _ in range(len(query_embeddings))], np.array([])

        # Ensure float32
        query_embeddings = query_embeddings.astype(np.float32)

        # Normalize for cosine similarity
        if self.metric == "IP" or "IP" in self.index_type:
            faiss.normalize_L2(query_embeddings)

        # Search
        k = min(k, self.index.ntotal)
        distances, indices = self.index.search(query_embeddings, k)

        # Get metadata for all results
        all_results = []
        for query_indices in indices:
            query_results = []
            for idx in query_indices:
                if idx >= 0 and idx < len(self.metadata):
                    query_results.append(self.metadata[idx])
            all_results.append(query_results)

        # Convert distances to similarities
        if "L2" in self.index_type:
            similarities = 1.0 / (1.0 + distances)
        else:
            similarities = distances

        return all_results, similarities

    def save(self, index_path: Path, metadata_path: Path):
        """
        Save index and metadata to disk

        Args:
            index_path: Path to save FAISS index
            metadata_path: Path to save metadata
        """
        index_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, str(index_path))

        # Save metadata
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                'metadata': self.metadata,
                'dimension': self.dimension,
                'index_type': self.index_type,
                'metric': self.metric,
                'nlist': self.nlist,
            }, f)

        logger.info(f"Saved database to {index_path} and {metadata_path}")

    def load(self, index_path: Path, metadata_path: Path):
        """
        Load index and metadata from disk

        Args:
            index_path: Path to FAISS index
            metadata_path: Path to metadata
        """
        # Load FAISS index
        self.index = faiss.read_index(str(index_path))

        # Load metadata
        with open(metadata_path, 'rb') as f:
            data = pickle.load(f)
            self.metadata = data['metadata']
            self.dimension = data['dimension']
            self.index_type = data['index_type']
            self.metric = data['metric']
            self.nlist = data.get('nlist', 100)

        logger.info(f"Loaded database with {self.index.ntotal} embeddings")

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            'total_embeddings': self.index.ntotal,
            'dimension': self.dimension,
            'index_type': self.index_type,
            'metric': self.metric,
            'metadata_count': len(self.metadata),
        }
