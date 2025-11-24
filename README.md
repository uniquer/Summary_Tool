# PDF Summarization Tool

A powerful web application built with Streamlit that downloads PDFs from URLs, extracts text and tables, and generates AI-powered summaries using Claude or OpenAI.

## Features

- **Batch Processing**: Process up to 500 PDF URLs in one session
- **AI-Powered**: Choose between Claude or OpenAI for summarization
- **Dual Summaries**: Generate both long and short summaries with custom prompts
- **Real-Time Monitoring**: Live progress updates and status tracking
- **Database Storage**: Save all summaries to Supabase for future reference
- **Excel Export**: Download comprehensive reports with all summaries
- **Table Extraction**: Extracts both text and tables from PDFs

## Prerequisites

- Python 3.8 or higher
- Supabase account (free tier works)
- API key for either:
  - Claude (Anthropic)
  - OpenAI

## Installation

### 1. Clone the Repository

```bash
cd Summary_Tool
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Supabase

1. Go to [Supabase](https://supabase.com) and create a new project
2. Once created, navigate to **SQL Editor**
3. Run the following SQL to create the summaries table:

```sql
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

-- Add index for faster queries
CREATE INDEX idx_created_at ON pdf_summaries(created_at DESC);
CREATE INDEX idx_status ON pdf_summaries(status);
```

4. Get your credentials:
   - Go to **Project Settings** → **API**
   - Copy **Project URL** (SUPABASE_URL)
   - Copy **anon/public** key (SUPABASE_KEY)

### 5. Get AI API Keys

#### For Claude (Recommended):
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create an account or sign in
3. Navigate to **API Keys**
4. Create a new API key

#### For OpenAI:
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Navigate to **API Keys**
4. Create a new API key

### 6. Create Files Folder

```bash
mkdir files
```

## Usage

### 1. Start the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

### 2. Configure Settings

In the sidebar:
- **AI Provider**: Choose between Claude or OpenAI
- **API Key**: Enter your API key
- **Supabase URL**: Enter your Supabase project URL
- **Supabase API Key**: Enter your Supabase API key

### 3. Add PDF URLs

In the left column:
- Paste PDF URLs, one per line (up to 500 URLs)
- The app will show the total count

Example:
```
https://arxiv.org/pdf/2301.00001.pdf
https://example.com/research-paper.pdf
https://documents.site.com/report-2024.pdf
```

### 4. Set Summary Prompts

In the right column, define your prompts:

**Long Summary Prompt Example:**
```
Please provide a comprehensive summary of this document that includes:
1. Main objectives and purpose
2. Key methodologies used
3. Important findings and results
4. Conclusions and recommendations
5. Any significant data, statistics, or tables mentioned

The summary should be detailed and capture all essential information.
```

**Short Summary Prompt Example:**
```
Please provide a concise 2-3 sentence summary that captures only the most critical points of this document. Focus on the main purpose and key outcome.
```

### 5. Start Processing

1. Click **"▶️ Start Summarization"**
2. Watch real-time progress and status updates
3. Results appear as each PDF is processed
4. Click **"⏹️ Stop"** to halt processing at any time

### 6. Review Results

- Expand each result to see:
  - Original URL
  - Downloaded filename
  - Long summary
  - Short summary
  - Status (success/failed)
  - Error messages (if any)

### 7. Download Excel Report

1. Click **"📥 Download Excel Report"**
2. Click **"💾 Click to Download"**
3. Excel file includes all URLs, filenames, summaries, and statuses

## Project Structure

```
Summary_Tool/
├── app.py                  # Main Streamlit application
├── pdf_processor.py        # PDF download and text extraction
├── summarizer.py           # AI summarization (Claude/OpenAI)
├── database.py             # Supabase integration
├── report_generator.py     # Excel report generation
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── files/                 # Downloaded PDFs (auto-created)
└── README.md              # This file
```

## Features in Detail

### PDF Processing
- **Smart Download**: Validates content type and handles errors gracefully
- **Text Extraction**: Uses pdfplumber for accurate text extraction
- **Table Detection**: Automatically extracts and formats tables
- **Page Limits**: Processes up to 100 pages per PDF to manage API costs

### Summarization
- **Dual Prompts**: Separate prompts for detailed and brief summaries
- **Chunking**: Automatically splits large documents for processing
- **Error Recovery**: Continues processing even if individual PDFs fail
- **Custom Instructions**: Full control over summary style and content

### Database
- **Persistent Storage**: All summaries saved to Supabase
- **Timestamps**: Track when each summary was created
- **Status Tracking**: Know which PDFs succeeded or failed
- **Error Logging**: Detailed error messages for troubleshooting

### Reporting
- **Excel Export**: Professional formatted reports
- **Multiple Columns**: URL, filename, both summaries, status, errors
- **Auto-Formatting**: Wrapped text, column widths, and filters
- **Statistics**: Success rate and processing summary

## Troubleshooting

### Common Issues

**"Error: No text content extracted from PDF"**
- The PDF might be image-based (scanned document)
- Try using OCR-enabled PDFs

**"HTTP error: 404"**
- Verify the URL is accessible and points directly to a PDF file
- Check if authentication is required

**"API error"**
- Verify your API key is correct and has credits
- Check API rate limits

**"Database error"**
- Verify Supabase credentials are correct
- Ensure the table was created properly
- Check internet connection

### Tips for Best Results

1. **Prompt Engineering**: Be specific about what you want in summaries
2. **Batch Size**: Start with 5-10 PDFs to test prompts before large batches
3. **URL Format**: Ensure URLs end with `.pdf` and are publicly accessible
4. **API Costs**: Monitor usage for Claude/OpenAI based on document sizes
5. **Network**: Stable internet connection recommended for large batches

## Cost Considerations

- **Claude**: ~$3 per million input tokens, ~$15 per million output tokens
- **OpenAI GPT-4**: Similar pricing structure
- **Supabase**: Free tier includes 500MB database (plenty for summaries)

For a typical 10-page PDF:
- Input tokens: ~5,000-10,000
- Output tokens: ~500-1,000
- Estimated cost: $0.10-0.30 per PDF

## Security Notes

- Never commit your API keys to version control
- Keep `.env` file out of git (already in `.gitignore`)
- Use environment variables for production deployments
- Rotate API keys regularly

## Future Enhancements

Potential improvements:
- [ ] OCR support for scanned PDFs
- [ ] Multiple file format support (DOCX, TXT, etc.)
- [ ] Parallel processing for faster batch operations
- [ ] Custom retry logic for failed downloads
- [ ] Summary comparison and diff views
- [ ] Export to other formats (PDF, DOCX, JSON)
- [ ] User authentication and multi-user support

## License

This project is open source and available under the MIT License.

## Support

For issues or questions:
1. Check this README
2. Review error messages in the app
3. Check Supabase logs
4. Verify API key validity

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

Built with ❤️ using Streamlit, Claude/OpenAI, and Supabase
