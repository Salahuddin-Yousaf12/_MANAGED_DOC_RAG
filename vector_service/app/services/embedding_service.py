"""
Embedding service for generating dense and sparse embeddings
"""
import re
import math
from typing import List, Dict, Tuple
from collections import Counter
from sentence_transformers import SentenceTransformer
from app.config import settings


class EmbeddingService:
    """
    Service for generating embeddings.
    - Dense embeddings: Using sentence-transformers
    - Sparse embeddings: Using BM25-style TF-IDF
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None

        # BM25 parameters
        self.k1 = 1.5  # Term frequency saturation
        self.b = 0.75  # Length normalization

        # Vocabulary for sparse embeddings (built dynamically)
        self._vocab: Dict[str, int] = {}
        self._vocab_counter = 0
        self._idf_scores: Dict[str, float] = {}
        self._avg_doc_length = 0
        self._doc_count = 0

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the embedding model"""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def generate_dense_embedding(self, text: str) -> List[float]:
        """
        Generate dense embedding using sentence-transformers.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the dense embedding
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def generate_dense_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate dense embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]

    def generate_sparse_embedding(self, text: str) -> Dict[int, float]:
        """
        Generate sparse embedding using BM25-style scoring.

        Args:
            text: Input text

        Returns:
            Dictionary mapping token indices to weights
        """
        tokens = self._tokenize(text)
        if not tokens:
            return {}

        # Calculate term frequencies
        tf = Counter(tokens)
        doc_length = len(tokens)

        sparse_vector = {}
        for token, freq in tf.items():
            # Get or create vocabulary index
            if token not in self._vocab:
                self._vocab[token] = self._vocab_counter
                self._vocab_counter += 1

            idx = self._vocab[token]

            # BM25 TF component
            tf_score = (freq * (self.k1 + 1)) / (
                freq + self.k1 * (1 - self.b + self.b * doc_length / max(self._avg_doc_length, 1))
            )

            # IDF component (use default if not computed)
            idf = self._idf_scores.get(token, 1.0)

            sparse_vector[idx] = tf_score * idf

        return sparse_vector

    def generate_sparse_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[Dict[int, float]]:
        """
        Generate sparse embeddings for multiple texts.
        Also updates IDF scores based on the batch.

        Args:
            texts: List of texts

        Returns:
            List of sparse embeddings
        """
        # First pass: build vocabulary and compute document frequencies
        doc_freqs: Dict[str, int] = Counter()
        tokenized_docs = []

        for text in texts:
            tokens = self._tokenize(text)
            tokenized_docs.append(tokens)
            # Count unique tokens per document
            doc_freqs.update(set(tokens))

        # Update IDF scores
        n_docs = len(texts)
        self._doc_count += n_docs

        for token, df in doc_freqs.items():
            # Smoothed IDF
            idf = math.log((self._doc_count - df + 0.5) / (df + 0.5) + 1)
            self._idf_scores[token] = max(idf, 0)  # Ensure non-negative

        # Update average document length
        total_length = sum(len(tokens) for tokens in tokenized_docs)
        self._avg_doc_length = (
            (self._avg_doc_length * (self._doc_count - n_docs) + total_length) /
            self._doc_count
        )

        # Second pass: generate sparse embeddings
        sparse_embeddings = []
        for tokens in tokenized_docs:
            if not tokens:
                sparse_embeddings.append({})
                continue

            tf = Counter(tokens)
            doc_length = len(tokens)

            sparse_vector = {}
            for token, freq in tf.items():
                if token not in self._vocab:
                    self._vocab[token] = self._vocab_counter
                    self._vocab_counter += 1

                idx = self._vocab[token]

                # BM25 score
                tf_score = (freq * (self.k1 + 1)) / (
                    freq + self.k1 * (1 - self.b + self.b * doc_length / max(self._avg_doc_length, 1))
                )
                idf = self._idf_scores.get(token, 1.0)
                sparse_vector[idx] = tf_score * idf

            sparse_embeddings.append(sparse_vector)

        return sparse_embeddings

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for sparse embeddings.
        Simple whitespace + punctuation tokenization with lowercasing.
        """
        # Lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b[a-z0-9]+\b', text)

        # Remove very short tokens and stopwords
        stopwords = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
            'that', 'the', 'to', 'was', 'were', 'will', 'with'
        }
        tokens = [t for t in tokens if len(t) > 2 and t not in stopwords]

        return tokens

    def get_embedding_dimension(self) -> int:
        """Get the dimension of dense embeddings"""
        return self.model.get_sentence_embedding_dimension()

    def get_vocab_size(self) -> int:
        """Get current vocabulary size for sparse embeddings"""
        return len(self._vocab)


# Global instance
embedding_service = EmbeddingService()
