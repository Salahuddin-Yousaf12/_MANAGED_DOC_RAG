"""
Semantic chunking service for splitting documents into meaningful chunks
"""
import re
from typing import List, Tuple
from app.config import settings


class ChunkingService:
    """
    Service for semantically chunking text documents.
    Uses sentence boundaries and paragraph structure for intelligent splitting.
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        min_chunk_size: int = None
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.min_chunk_size = min_chunk_size or settings.MIN_CHUNK_SIZE

        # Sentence ending patterns
        self.sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        # Paragraph pattern
        self.paragraph_pattern = re.compile(r'\n\s*\n')

    def chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Split text into semantic chunks.

        Args:
            text: The input text to chunk

        Returns:
            List of tuples: (chunk_text, start_char, end_char)
        """
        if not text or not text.strip():
            return []

        # Clean the text
        text = self._clean_text(text)

        # First, split by paragraphs
        paragraphs = self._split_into_paragraphs(text)

        # Then create chunks respecting sentence boundaries
        chunks = self._create_chunks(paragraphs, text)

        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        paragraphs = self.paragraph_pattern.split(text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentences = self.sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def _create_chunks(
        self,
        paragraphs: List[str],
        original_text: str
    ) -> List[Tuple[str, int, int]]:
        """
        Create chunks from paragraphs, respecting sentence boundaries.

        Returns list of (chunk_text, start_position, end_position)
        """
        chunks = []
        current_chunk = []
        current_length = 0
        current_start = 0

        for paragraph in paragraphs:
            sentences = self._split_into_sentences(paragraph)

            if not sentences:
                sentences = [paragraph]

            for sentence in sentences:
                sentence_length = len(sentence)

                # If adding this sentence exceeds chunk size
                if current_length + sentence_length > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunk_text = ' '.join(current_chunk)
                    chunk_start = original_text.find(current_chunk[0], current_start)
                    chunk_end = chunk_start + len(chunk_text)

                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append((chunk_text, chunk_start, chunk_end))

                    # Start new chunk with overlap
                    overlap_sentences = self._get_overlap_sentences(
                        current_chunk, self.chunk_overlap
                    )
                    current_chunk = overlap_sentences + [sentence]
                    current_length = sum(len(s) for s in current_chunk)
                    current_start = chunk_end - self.chunk_overlap
                else:
                    current_chunk.append(sentence)
                    current_length += sentence_length

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk_start = original_text.find(current_chunk[0], current_start)
            if chunk_start == -1:
                chunk_start = max(0, len(original_text) - len(chunk_text))
            chunk_end = chunk_start + len(chunk_text)

            if len(chunk_text) >= self.min_chunk_size:
                chunks.append((chunk_text, chunk_start, chunk_end))

        return chunks

    def _get_overlap_sentences(
        self,
        sentences: List[str],
        target_overlap: int
    ) -> List[str]:
        """Get sentences from the end that approximately match overlap size"""
        overlap_sentences = []
        current_length = 0

        for sentence in reversed(sentences):
            if current_length + len(sentence) <= target_overlap:
                overlap_sentences.insert(0, sentence)
                current_length += len(sentence)
            else:
                break

        return overlap_sentences

    def get_chunk_count(self, text: str) -> int:
        """Get estimated number of chunks for a text"""
        return len(self.chunk_text(text))


# Global instance
chunking_service = ChunkingService()
