"""知識庫服務層"""
from __future__ import annotations

from pgvector.django import CosineDistance

from .models import KnowledgeEntry


def search_similar(
    query: str,
    category: str | None = None,
    visibility: str | None = None,
    verified_only: bool = True,
    threshold: float = 0.5,
    top_k: int = 5,
) -> list[dict]:
    """向量相似度搜尋

    Args:
        query:        使用者輸入的問題
        category:     限定類別（None = 全部）
        visibility:   限定可見範圍 'internal'/'public'（None = 全部）
        verified_only: 只搜已審核的條目
        threshold:    餘弦距離上限（距離越小越相似；0.5 約等於相似度 0.5）
        top_k:        最多回傳幾筆

    Returns:
        list of dict，每筆包含 entry + distance + similarity
    """
    from core.services.embedding import get_embedding

    query_vec = get_embedding(query, task_type='RETRIEVAL_QUERY')

    qs = KnowledgeEntry.objects.filter(is_deleted=False, embedding__isnull=False)

    if verified_only:
        qs = qs.filter(is_verified=True)
    if category:
        qs = qs.filter(category=category)
    if visibility:
        qs = qs.filter(visibility=visibility)

    results = (
        qs
        .annotate(distance=CosineDistance('embedding', query_vec))
        .filter(distance__lte=threshold)
        .order_by('distance')[:top_k]
    )

    return [
        {
            'entry': r,
            'distance': round(r.distance, 4),
            'similarity': round(1 - r.distance, 4),
        }
        for r in results
    ]
