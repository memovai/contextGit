"""Text chunking utilities for vector database storage."""

from typing import List


class TextChunker:
    """Utility class for chunking text into smaller pieces for vector storage."""

    def __init__(self, chunk_size: int = 768, overlap: int = 100):
        """
        Initialize the text chunker.

        Args:
            chunk_size: Maximum size of each chunk in characters (default: 768)
            overlap: Number of overlapping characters between chunks (default: 100)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks of specified size with overlap.

        Args:
            text: The text to chunk

        Returns:
            List of text chunks
        """
        if not text:
            return []

        # If text is shorter than chunk_size, return as single chunk
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size

            # If this is not the last chunk, try to break at a space
            if end < len(text):
                # Look for the last space within the chunk
                last_space = text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space

            # Extract chunk
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = end - self.overlap if end < len(text) else end

            # Prevent infinite loop
            if start <= chunks[-1] if chunks else 0:
                start = end

        return chunks

    def chunk_with_metadata(
        self, text: str, base_metadata: dict
    ) -> List[tuple[str, dict]]:
        """
        Chunk text and create metadata for each chunk.

        Args:
            text: The text to chunk
            base_metadata: Base metadata to attach to each chunk

        Returns:
            List of tuples containing (chunk_text, chunk_metadata)
        """
        chunks = self.chunk_text(text)
        result = []

        for idx, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = idx
            chunk_metadata["total_chunks"] = len(chunks)
            chunk_metadata["chunk_text"] = chunk
            result.append((chunk, chunk_metadata))

        return result
