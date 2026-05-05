"""Embedding 服務 - 封裝 Gemini text-embedding-004

從 SystemParameter (key='GEMINI_API_KEY') 讀取 API key。
產生 768 維向量，可直接寫入 pgvector VectorField。
"""
from __future__ import annotations

import logging
from typing import Iterable

from modules.system_config.helpers import get_system_param

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = 'gemini-embedding-001'
EMBEDDING_DIMENSIONS = 768


def _get_client():
    from google import genai
    api_key = get_system_param('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError(
            'GEMINI_API_KEY 未設定，請至 admin/system_config/systemparameter/ 新增'
        )
    return genai.Client(api_key=api_key)


def get_embedding(text: str, task_type: str = 'RETRIEVAL_DOCUMENT') -> list[float]:
    """為單筆文字產生 embedding 向量。

    task_type:
      - RETRIEVAL_DOCUMENT: 用於入庫的知識條目
      - RETRIEVAL_QUERY:    用於查詢時的關鍵字
    """
    text = (text or '').strip()
    if not text:
        raise ValueError('text 不可為空')
    client = _get_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={'task_type': task_type, 'output_dimensionality': EMBEDDING_DIMENSIONS},
    )
    return result.embeddings[0].values


def get_embeddings_batch(texts: Iterable[str], task_type: str = 'RETRIEVAL_DOCUMENT') -> list[list[float]]:
    """批次產生 embedding"""
    cleaned = [(t or '').strip() for t in texts]
    cleaned = [t for t in cleaned if t]
    if not cleaned:
        return []
    client = _get_client()
    results = []
    for text in cleaned:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config={'task_type': task_type, 'output_dimensionality': EMBEDDING_DIMENSIONS},
        )
        results.append(result.embeddings[0].values)
    return results
