-- PDF Summaries Table Creation Script
-- Run this in your Supabase SQL Editor

-- Create the main summaries table
CREATE TABLE IF NOT EXISTS pdf_summaries (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    filename TEXT NOT NULL,
    long_summary TEXT,
    short_summary TEXT,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_created_at ON pdf_summaries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_status ON pdf_summaries(status);
CREATE INDEX IF NOT EXISTS idx_url ON pdf_summaries(url);

-- Add a trigger to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_pdf_summaries_updated_at
    BEFORE UPDATE ON pdf_summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Optional: Add comments to columns for documentation
COMMENT ON TABLE pdf_summaries IS 'Stores PDF summary data including URLs, extracted content, and AI-generated summaries';
COMMENT ON COLUMN pdf_summaries.url IS 'Original URL of the PDF file';
COMMENT ON COLUMN pdf_summaries.filename IS 'Downloaded filename of the PDF';
COMMENT ON COLUMN pdf_summaries.long_summary IS 'Detailed AI-generated summary';
COMMENT ON COLUMN pdf_summaries.short_summary IS 'Brief AI-generated summary';
COMMENT ON COLUMN pdf_summaries.status IS 'Processing status: pending, success, or failed';
COMMENT ON COLUMN pdf_summaries.error_message IS 'Error details if processing failed';

-- Verify table creation
SELECT 'Table created successfully!' AS status;
SELECT * FROM pdf_summaries LIMIT 1;
