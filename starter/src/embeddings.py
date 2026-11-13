import math
import os
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from openai import APIError, OpenAI


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    def __init__(self, model_name: str | None = None, *,
                 dimensions: int | None = None, batch_size: int = 64) -> None:
        load_dotenv(Path(__file__).resolve().parents[1] / '.env')
        self.model_name = (model_name or os.getenv('EMBEDDING_MODEL') or
                           'openai/text-embedding-3-small').strip()
        if not self.model_name:
            raise ValueError('EMBEDDING_MODEL must not be blank.')
        key = os.getenv('OPENROUTER_API_KEY', '').strip()
        if not key:
            raise ValueError('Set OPENROUTER_API_KEY in starter/.env.')
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError('batch_size must be a positive integer.')
        configured = os.getenv('EMBEDDING_DIMENSIONS', '').strip()
        if dimensions is None and configured:
            try:
                dimensions = int(configured)
            except ValueError:
                raise ValueError('EMBEDDING_DIMENSIONS must be a positive integer.') from None
        # Only send dimensions when explicitly requested: some models do not
        # support changing their native output size.
        self._requested_dimensions = dimensions
        native_sizes = {'openai/text-embedding-3-small': 1536,
                        'openai/text-embedding-3-large': 3072,
                        'openai/text-embedding-ada-002': 1536}
        self.dimensions = dimensions if dimensions is not None else native_sizes.get(self.model_name)
        if type(self.dimensions) is not int or self.dimensions < 1:
            raise ValueError('Supply positive dimensions or EMBEDDING_DIMENSIONS for this model.')
        self.batch_size = batch_size
        self._client = OpenAI(api_key=key, base_url='https://openrouter.ai/api/v1',
                              timeout=60.0, max_retries=2)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not isinstance(texts, list):
            raise TypeError('texts must be a list of strings.')
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError('Every input must be a non-empty string.')
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            options = {}
            if self._requested_dimensions is not None:
                options['dimensions'] = self._requested_dimensions
            try:
                response = self._client.embeddings.create(
                    model=self.model_name, input=batch, encoding_format='float', **options)
            except APIError as error:
                # Do not include provider bodies, keys or source text in errors.
                status = getattr(error, 'status_code', None)
                raise RuntimeError(
                    f'OpenRouter embedding request failed ({type(error).__name__}, '
                    f'status={status}, batch_start={start}). Check credentials, '
                    'credits, model availability and input limits; no fallback was used.'
                ) from None
            items = sorted(response.data, key=lambda item: item.index)
            if [item.index for item in items] != list(range(len(batch))):
                raise RuntimeError('OpenRouter returned missing, duplicate or invalid embedding indices.')
            for item in items:
                vector = item.embedding
                if (len(vector) != self.dimensions or
                        any(type(value) not in (int, float) or not math.isfinite(value)
                            for value in vector) or not any(vector)):
                    raise RuntimeError('OpenRouter returned an invalid vector or unexpected dimensions.')
                vectors.append(vector)
        return vectors

    def embed_query(self, question: str) -> list[float]:
        return self.embed_documents([question])[0]

    def close(self) -> None:
        self._client.close()
