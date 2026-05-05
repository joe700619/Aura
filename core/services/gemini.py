"""Gemini 生成式 AI 服務 - 用於文字摘要、Q&A 萃取等任務"""
from __future__ import annotations

import logging

from modules.system_config.helpers import get_system_param

logger = logging.getLogger(__name__)

GENERATION_MODEL = 'gemini-2.5-flash'


def _get_client():
    from google import genai
    api_key = get_system_param('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY 未設定')
    return genai.Client(api_key=api_key)


def summarize_case_for_kb(case) -> dict:
    """從案件的標題、摘要、對話紀錄、清單，產生適合存入知識庫的 Q&A 摘要。

    Returns:
        {'question_summary': str, 'answer_summary': str}
    """
    # 組合對話紀錄（排除系統 log，只送文字內容）
    replies = case.replies.filter(
        is_deleted=False, is_system_log=False
    ).order_by('created_at').select_related('author_user')

    conversation_lines = []
    for r in replies:
        if r.author_type == 'internal':
            speaker = r.author_user.get_full_name() if r.author_user else '內部人員'
            role = f'【內部】{speaker}'
        elif r.author_type == 'external':
            role = f'【客戶】{r.author_display_name or "客戶"}'
        else:
            continue  # 跳過 system 類型
        conversation_lines.append(f'{role}：{r.content.strip()}')

    # 組合清單（只取文字標題）
    tasks = case.tasks.filter(is_deleted=False).order_by('order', 'created_at')
    task_lines = [f'- [{t.get_assignee_type_display()}] {t.title}' for t in tasks]

    # 組合完整 prompt
    parts = []
    parts.append(f'案件標題：{case.title}')
    if case.summary:
        parts.append(f'問題摘要：{case.summary}')
    if task_lines:
        parts.append('清單（需準備文件 / 待辦）：\n' + '\n'.join(task_lines))
    if conversation_lines:
        parts.append('對話紀錄：\n' + '\n'.join(conversation_lines))

    case_text = '\n\n'.join(parts)

    prompt = f"""你是一個會計事務所的知識管理助理。
請根據以下案件內容，萃取出可重複使用的知識，輸出 JSON 格式，包含四個欄位：
- question_summary：清楚描述這個案件解決了什麼問題（1–3 句話，去除個人識別資訊）
- answer_summary：詳細的解答說明，包含解決步驟、注意事項（3–8 句話，去除個人識別資訊；不要包含文件清單，那會放在 checklist 欄位）
- checklist：需要準備的文件或待辦項目清單，來自案件清單，每個項目一行純文字，若沒有清單則回傳空字串
- category：從以下選項中選擇最符合的一個（只回傳代碼）：
  tax_filing（稅務申報）、invoice（發票管理）、payroll（薪資勞健保）、
  financial（財務報表）、accounting（會計處理）、incorporation（公司登記）、
  inheritance（遺產贈與）、other（其他）

請直接輸出 JSON，不要加任何說明文字或 markdown 標記。

案件內容：
{case_text}
"""

    client = _get_client()
    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
    )

    raw = response.text.strip()
    # 清除可能的 markdown code block
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[-1]
        raw = raw.rsplit('```', 1)[0].strip()

    import json
    data = json.loads(raw)
    valid_categories = {c[0] for c in [
        ('tax_filing', ''), ('invoice', ''), ('payroll', ''), ('financial', ''),
        ('accounting', ''), ('incorporation', ''), ('inheritance', ''), ('other', ''),
    ]}
    category = data.get('category', 'other')
    if category not in valid_categories:
        category = 'other'

    return {
        'question_summary': data.get('question_summary', case.title),
        'answer_summary': data.get('answer_summary', ''),
        'checklist': data.get('checklist', ''),
        'category': category,
    }
