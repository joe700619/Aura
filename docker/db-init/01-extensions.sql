-- 自動啟用 pgvector extension（Aura knowledge_base 的 embedding 欄位需要）
-- 此檔案會在第一次建立 DB volume 時自動執行

CREATE EXTENSION IF NOT EXISTS vector;
