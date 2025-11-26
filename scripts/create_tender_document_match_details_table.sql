-- Таблица детальных совпадений по документам торга

CREATE TABLE IF NOT EXISTS tender_document_match_details (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES tender_document_matches(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    sheet_name TEXT,
    row_index INTEGER,
    column_letter TEXT,
    cell_address TEXT,
    source_file TEXT,
    matched_text TEXT,
    matched_display_text TEXT,
    matched_keywords TEXT[],
    row_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_match_details_match_id ON tender_document_match_details(match_id);

