"""
PDF Summarization Tool - Streamlit Web App
"""
import streamlit as st
from datetime import datetime
import os
from typing import Dict, List
import time
# Load environment variables
# load_dotenv() - Removed, using st.secrets instead

from pdf_processor import PDFProcessor
from summarizer import Summarizer
from database import SummaryDatabase
from report_generator import ReportGenerator
# Force reload


# Page configuration
st.set_page_config(
    page_title="PDF Summary Tool",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'stop_processing' not in st.session_state:
    st.session_state.stop_processing = False
if 'processed_items' not in st.session_state:
    st.session_state.processed_items = []
if 'session_start' not in st.session_state:
    st.session_state.session_start = None
if 'file_results' not in st.session_state:
    st.session_state.file_results = []
if 'processing_phase' not in st.session_state:
    st.session_state.processing_phase = None  # 'download' or 'summarize'


def initialize_components(ai_provider: str, api_key: str, supabase_url: str, supabase_key: str):
    """
    Initialize all components

    Returns:
        Tuple of (pdf_processor, summarizer, database, report_generator)
    """
    try:
        pdf_processor = PDFProcessor(download_folder="files")
        summarizer = Summarizer(provider=ai_provider, api_key=api_key)
        database = SummaryDatabase(supabase_url=supabase_url, supabase_key=supabase_key)
        report_generator = ReportGenerator()
        return pdf_processor, summarizer, database, report_generator, None
    except Exception as e:
        return None, None, None, None, str(e)


def download_pdf_file(url: str, pdf_processor, skip_existing: bool = True) -> Dict:
    """
    Download a single PDF file

    Args:
        url: PDF URL
        pdf_processor: PDFProcessor instance
        skip_existing: Skip if file already exists

    Returns:
        Dictionary with download results
    """
    result = {
        'url': url,
        'filename': '',
        'extracted_text': '',
        'download_status': 'pending',
        'download_error': '',
        'summary_status': 'pending',
        'long_summary': '',
        'short_summary': '',
        'summary_error': ''
    }

    try:
        # Check if file already exists
        expected_filename = pdf_processor.get_expected_filename(url)
        file_exists = pdf_processor.file_exists(expected_filename)

        if file_exists and skip_existing:
            result['filename'] = expected_filename
            result['download_status'] = 'skipped'
            # Extract text for later summarization
            filepath = os.path.join(pdf_processor.download_folder, expected_filename)
            success, extracted_text, error = pdf_processor.extract_text_and_tables(filepath)
            if success:
                result['extracted_text'] = extracted_text
            else:
                result['download_status'] = 'failed'
                result['download_error'] = f"Text extraction failed: {error}"
            return result

        # Download and extract PDF
        if file_exists:
            filepath = os.path.join(pdf_processor.download_folder, expected_filename)
            success, extracted_text, error = pdf_processor.extract_text_and_tables(filepath)
            filename = expected_filename
        else:
            success, filename, extracted_text, error = pdf_processor.process_pdf(url)

        if not success:
            result['download_status'] = 'failed'
            result['download_error'] = error
            return result

        result['filename'] = filename
        result['extracted_text'] = extracted_text
        result['download_status'] = 'success'

        return result

    except Exception as e:
        result['download_status'] = 'failed'
        result['download_error'] = f"Unexpected error: {str(e)}"
        return result


def summarize_pdf(result: Dict, summarizer, database, long_prompt: str, short_prompt: str) -> Dict:
    """
    Summarize a PDF that has been downloaded

    Args:
        result: Dictionary with download results
        summarizer: Summarizer instance
        database: SummaryDatabase instance
        long_prompt: Long summary prompt
        short_prompt: Short summary prompt

    Returns:
        Updated dictionary with summarization results
    """
    try:
        if result['download_status'] != 'success' and result['download_status'] != 'skipped':
            result['summary_status'] = 'skipped'
            result['summary_error'] = 'Download failed or pending'
            return result

        if not result['extracted_text']:
            result['summary_status'] = 'failed'
            result['summary_error'] = 'No extracted text available'
            return result

        # Generate summaries
        success, long_summary, short_summary, error = summarizer.create_summaries(
            result['extracted_text'], long_prompt, short_prompt
        )

        if not success:
            result['summary_status'] = 'failed'
            result['summary_error'] = error
            # Save failed attempt to database
            database.insert_summary({
                'url': result['url'],
                'filename': result['filename'],
                'long_summary': f"FAILED: {error}",
                'short_summary': f"FAILED: {error}",
                'status': 'failed',
                'error_message': error,
                'created_at': datetime.utcnow().isoformat()
            })
            return result

        # Update result with summaries
        result['long_summary'] = long_summary
        result['short_summary'] = short_summary
        result['summary_status'] = 'success'

        # Save to database
        database.insert_summary({
            'url': result['url'],
            'filename': result['filename'],
            'long_summary': long_summary,
            'short_summary': short_summary,
            'status': 'success',
            'error_message': '',
            'created_at': datetime.utcnow().isoformat()
        })

        return result

    except Exception as e:
        result['summary_status'] = 'failed'
        result['summary_error'] = f"Unexpected error: {str(e)}"
        return result


def process_single_pdf(url: str, pdf_processor, summarizer, database, long_prompt: str, short_prompt: str,
                       status_placeholder, progress_text, skip_existing: bool = True) -> Dict:
    """
    Process a single PDF: download, extract, summarize, and save

    Args:
        url: PDF URL
        pdf_processor: PDFProcessor instance
        summarizer: Summarizer instance
        database: SummaryDatabase instance
        long_prompt: Long summary prompt
        short_prompt: Short summary prompt
        status_placeholder: Streamlit placeholder for status updates
        progress_text: Streamlit placeholder for progress text
        skip_existing: Skip if file already exists

    Returns:
        Dictionary with processing results
    """
    result = {
        'url': url,
        'filename': '',
        'long_summary': '',
        'short_summary': '',
        'status': 'failed',
        'error_message': '',
        'created_at': datetime.utcnow().isoformat()
    }

    try:
        # Check if file already exists
        expected_filename = pdf_processor.get_expected_filename(url)
        file_exists = pdf_processor.file_exists(expected_filename)

        if file_exists and skip_existing:
            result['filename'] = expected_filename
            result['status'] = 'skipped'
            status_placeholder.warning(f"⏭️ Skipped: {expected_filename} (already exists)")
            return result

        # Update status
        if file_exists:
            status_placeholder.info(f"📄 Using existing file: {expected_filename}")
            filepath = os.path.join(pdf_processor.download_folder, expected_filename)
            success, extracted_text, error = pdf_processor.extract_text_and_tables(filepath)
            if not success:
                result['error_message'] = error
                result['long_summary'] = f"FAILED: {error}"
                result['short_summary'] = f"FAILED: {error}"
                status_placeholder.error(f"❌ Extraction failed: {error}")
                database.insert_summary(result)
                return result
            filename = expected_filename
            result['filename'] = filename
        else:
            status_placeholder.info(f"📥 Downloading PDF from: {url[:80]}...")
            # Download and extract PDF
            success, filename, extracted_text, error = pdf_processor.process_pdf(url)

            if not success:
                result['error_message'] = error
                result['long_summary'] = f"FAILED: {error}"
                result['short_summary'] = f"FAILED: {error}"
                status_placeholder.error(f"❌ Download failed: {error}")
                database.insert_summary(result)
                return result

            result['filename'] = filename
            status_placeholder.success(f"✅ Downloaded: {filename}")

        # Update status for summarization
        progress_text.text(f"🤖 Generating summaries for {filename}...")

        # Generate summaries
        success, long_summary, short_summary, error = summarizer.create_summaries(
            extracted_text, long_prompt, short_prompt
        )

        if not success:
            result['error_message'] = error
            result['long_summary'] = f"FAILED: {error}"
            result['short_summary'] = f"FAILED: {error}"
            status_placeholder.error(f"❌ Summarization failed: {error}")
            database.insert_summary(result)
            return result

        # Update result with summaries
        result['long_summary'] = long_summary
        result['short_summary'] = short_summary
        result['status'] = 'success'

        # Save to database
        database.insert_summary(result)

        status_placeholder.success(f"✅ Completed: {filename}")

        return result

    except Exception as e:
        result['error_message'] = f"Unexpected error: {str(e)}"
        result['long_summary'] = f"FAILED: {str(e)}"
        result['short_summary'] = f"FAILED: {str(e)}"
        status_placeholder.error(f"❌ Error: {str(e)}")
        database.insert_summary(result)
        return result


def main():
    """Main application"""

    # Title and description
    st.title("📄 PDF Summarization Tool")
    st.markdown("Upload multiple PDF URLs and generate AI-powered summaries")

    # Create tabs for different sections
    tab1, tab2 = st.tabs(["📥 Download PDF Link", "📚 Existing Files"])

    # Sidebar - Configuration
    with st.sidebar:
        # Load from secrets.toml
        env_ai_provider = st.secrets.get("AI_PROVIDER", "")
        env_claude_key = st.secrets.get("CLAUDE_API_KEY", "")
        env_openai_key = st.secrets.get("OPENAI_API_KEY", "")
        env_openrouter_key = st.secrets.get("OPENROUTER_API_KEY", "")
        env_supabase_url = st.secrets.get("SUPABASE_URL", "")
        env_supabase_key = st.secrets.get("SUPABASE_KEY", "")

        # Set variables directly from secrets
        ai_provider = env_ai_provider
        supabase_url = env_supabase_url
        supabase_key = env_supabase_key
        
        # Determine API key based on provider
        api_key = ""
        if ai_provider.lower() == "claude":
            api_key = env_claude_key
        elif ai_provider.lower() == "openai":
            api_key = env_openai_key
        elif ai_provider.lower() == "openrouter":
            api_key = env_openrouter_key

        # Instructions
        with st.expander("📖 How to Use"):
            st.markdown("""
            1. **Add URLs**: Paste PDF URLs (one per line)
            2. **Start**: Click 'Download PDFs'
            3. **Monitor**: Watch real-time progress
            4. **Summarize**: Go to 'Existing Files' tab to generate summaries
            5. **Download**: Export results to Excel
            """)

    # Tab 1: New Summaries
    with tab1:
        # Main content area
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📋 PDF URLs")
            urls_input = st.text_area(
                "Enter PDF URLs (one per line)",
                height=300,
                placeholder="https://example.com/document1.pdf\nhttps://example.com/document2.pdf\n...",
                help="You can paste up to 500 URLs, one per line"
            )

            # Parse URLs
            urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
            st.info(f"📊 Total URLs: {len(urls)}")

        with col2:
            st.info("ℹ️ Note: This tab only downloads files. Go to 'Existing Files' tab to generate summaries.")

        # Control buttons
        st.divider()

        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 3])

        with col_btn1:
            start_button = st.button(
                "⬇️ Download PDFs",
                type="primary",
                disabled=st.session_state.processing,
                use_container_width=True
            )

        with col_btn2:
            stop_button = st.button(
                "⏹️ Stop",
                disabled=not st.session_state.processing,
                use_container_width=True
            )

        with col_btn3:
            clear_button = st.button(
                "🗑️ Clear Results",
                use_container_width=True
            )

        # Validation and processing
        if start_button:
            # Validate inputs
            errors = []

            if not api_key:
                errors.append(f"❌ {ai_provider} API key is required")
            if not supabase_url:
                errors.append("❌ Supabase URL is required")
            if not supabase_key:
                errors.append("❌ Supabase API key is required")
            if not urls:
                errors.append("❌ At least one PDF URL is required")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Initialize components
                pdf_processor, summarizer, database, report_generator, init_error = initialize_components(
                    ai_provider.lower(), api_key, supabase_url, supabase_key
                )

                if init_error:
                    st.error(f"❌ Initialization error: {init_error}")
                else:
                    # Start processing
                    st.session_state.processing = True
                    st.session_state.stop_processing = False
                    st.session_state.file_results = []
                    st.session_state.session_start = datetime.utcnow()
                    st.session_state.processing_phase = 'download'

                    # Processing UI
                    st.subheader("🔄 Processing Status")

                    # Phase 1: Download all PDFs
                    st.markdown("### Phase 1: Downloading PDFs")
                    download_progress = st.progress(0)
                    download_status = st.empty()

                    for idx, url in enumerate(urls):
                        if st.session_state.stop_processing:
                            st.warning("⏸️ Processing stopped by user")
                            break

                        download_status.info(f"📥 Downloading {idx + 1}/{len(urls)}: {url[:60]}...")
                        result = download_pdf_file(url, pdf_processor, skip_existing=True)
                        st.session_state.file_results.append(result)
                        
                        # Save URL to database for later retrieval
                        if result['download_status'] in ['success', 'skipped'] and result.get('filename'):
                            database.insert_summary({
                                'url': url,
                                'filename': result['filename'],
                                'long_summary': '',
                                'short_summary': '',
                                'status': 'pending',
                                'error_message': '',
                                'created_at': datetime.utcnow().isoformat()
                            })

                        # Update progress
                        download_progress.progress((idx + 1) / len(urls))

                    download_status.success(f"✅ Download phase complete! {len(st.session_state.file_results)} files processed")
                    st.session_state.processing = False
                    st.session_state.processing_phase = None

                    # Display status table after downloads
                    st.divider()
                    # Removed intermediate status table as requested

                    # Show statistics
                    successful_downloads = sum(1 for r in st.session_state.file_results if r['download_status'] == 'success')
                    skipped_downloads = sum(1 for r in st.session_state.file_results if r['download_status'] == 'skipped')
                    failed_downloads = sum(1 for r in st.session_state.file_results if r['download_status'] == 'failed')

                    st.success(f"""
                    **Download Summary**: {successful_downloads} downloaded, {skipped_downloads} skipped (already exists), {failed_downloads} failed
                    """)

        if stop_button:
            st.session_state.stop_processing = True
            st.session_state.processing = False

        if clear_button:
            st.session_state.file_results = []
            st.session_state.processed_items = []
            st.rerun()

        # Display existing results from file_results
        if st.session_state.file_results and not st.session_state.processing:
            st.divider()
            st.subheader("📊 Status of Downloaded Files")

            # Display status table
            # Display status table
            display_status_table(st.session_state.file_results, pdf_processor if 'pdf_processor' in locals() else None,
                               summarizer if 'summarizer' in locals() else None,
                               database if 'database' in locals() else None,
                               "", "", key_prefix="results", show_summary_status=False)

            # Download Excel Report
            st.divider()
            if st.button("📥 Summary of Download", type="primary", key="download_report_tab1"):
                try:
                    report_gen = ReportGenerator()
                    excel_file = report_gen.create_download_report(st.session_state.file_results)

                    with open(excel_file, 'rb') as f:
                        st.download_button(
                            label="💾 Click to Download",
                            data=f,
                            file_name=excel_file,
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            key="download_excel_tab1"
                        )

                    # Clean up file after download
                    if os.path.exists(excel_file):
                        os.remove(excel_file)

                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")

    # Tab 2: Existing Files
    with tab2:
        st.subheader("📚 Existing PDF Files")

        # Try to initialize components if credentials are available
        if api_key and supabase_url and supabase_key:
            pdf_processor, summarizer, database, report_generator, init_error = initialize_components(
                ai_provider.lower(), api_key, supabase_url, supabase_key
            )

            if not init_error:
                # List all files
                existing_files = pdf_processor.list_all_files()

                if existing_files:
                    st.info(f"Found {len(existing_files)} PDF files in the files folder")

                    st.divider()
                    st.subheader("💬 Summary Prompts")

                    # Load prompts from secrets.toml
                    long_prompt = st.secrets.get("LONG_SUMMARY_PROMPT", "")
                    short_prompt = st.secrets.get("SHORT_SUMMARY_PROMPT", "")
                    
                    # Display prompts in expander instead of inputs
                    with st.expander("📝 View Summary Prompts"):
                        st.markdown("**Long Summary Prompt:**")
                        st.caption(long_prompt)
                        st.divider()
                        st.markdown("**Short Summary Prompt:**")
                        st.caption(short_prompt)

                    st.divider()

                    # Summarize All Button
                    col_sum1, col_sum2 = st.columns([2, 1])
                    with col_sum1:
                        summarize_btn = st.button("🚀 Summarize All Files", type="primary", key="summarize_all_existing")
                    with col_sum2:
                        force_resummarize = st.checkbox("Force re-summarize all files", help="Check this to re-process all files, even those already summarized")

                    if summarize_btn:
                        if not long_prompt or not short_prompt:
                            st.error("❌ Please set long and short summary prompts above first")
                        else:
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            success_count = 0
                            fail_count = 0
                            skipped_count = 0
                            
                            files_to_process = []
                            for f in existing_files:
                                # Check if already summarized
                                should_process = False
                                summary = database.get_summary_by_filename(f)
                                
                                if force_resummarize:
                                    should_process = True
                                elif not summary:
                                    should_process = True
                                elif summary.get('status') != 'success':
                                    should_process = True
                                elif not summary.get('long_summary'): # Check for empty content even if status is success
                                    should_process = True
                                
                                if should_process:
                                    files_to_process.append(f)
                                else:
                                    skipped_count += 1
                            
                            if not files_to_process:
                                st.info("✨ All files are already summarized!")
                            else:
                                st.info(f"Processing {len(files_to_process)} files ({skipped_count} skipped)...")
                                
                                for i, filename in enumerate(files_to_process):
                                    status_text.text(f"Processing {i+1}/{len(files_to_process)}: {filename}...")
                                    
                                    # Try to get existing URL from database
                                    existing_url = ''
                                    existing_summary = database.get_summary_by_filename(filename)
                                    if existing_summary and existing_summary.get('url'):
                                        existing_url = existing_summary.get('url')
                                    
                                    try:
                                        # Extract text
                                        filepath = os.path.join(pdf_processor.download_folder, filename)
                                        success, extracted_text, error = pdf_processor.extract_text_and_tables(filepath)
                                        
                                        if not success:
                                            fail_count += 1
                                            error_msg = f"Text extraction failed: {error}"
                                            # Save failure to database
                                            result = {
                                                'url': existing_url,
                                                'filename': filename,
                                                'long_summary': f"FAILED: {error_msg}",
                                                'short_summary': f"FAILED: {error_msg}",
                                                'status': 'failed',
                                                'error_message': error_msg,
                                                'created_at': datetime.utcnow().isoformat()
                                            }
                                            database.insert_summary(result)
                                        else:
                                            # Generate summaries
                                            success, long_summary, short_summary, error = summarizer.create_summaries(
                                                extracted_text, long_prompt, short_prompt
                                            )
                                            
                                            if success:
                                                # Save to database
                                                result = {
                                                    'url': existing_url,
                                                    'filename': filename,
                                                    'long_summary': long_summary,
                                                    'short_summary': short_summary,
                                                    'status': 'success',
                                                    'error_message': '',
                                                    'created_at': datetime.utcnow().isoformat()
                                                }
                                                database.insert_summary(result)
                                                success_count += 1
                                            else:
                                                fail_count += 1
                                                error_msg = f"Summarization failed: {error}"
                                                # Save failure to database
                                                result = {
                                                    'url': existing_url,
                                                    'filename': filename,
                                                    'long_summary': f"FAILED: {error_msg}",
                                                    'short_summary': f"FAILED: {error_msg}",
                                                    'status': 'failed',
                                                    'error_message': error_msg,
                                                    'created_at': datetime.utcnow().isoformat()
                                                }
                                                database.insert_summary(result)
                                            
                                    except Exception as e:
                                        fail_count += 1
                                        error_msg = f"Error processing {filename}: {str(e)}"
                                        st.error(error_msg)
                                        # Save failure to database
                                        result = {
                                            'url': existing_url,
                                            'filename': filename,
                                            'long_summary': f"FAILED: {error_msg}",
                                            'short_summary': f"FAILED: {error_msg}",
                                            'status': 'failed',
                                            'error_message': error_msg,
                                            'created_at': datetime.utcnow().isoformat()
                                        }
                                        database.insert_summary(result)
                                
                                    # Update progress
                                    progress_bar.progress((i + 1) / len(files_to_process))
                                    
                                    # Rate limit delay
                                    time.sleep(2)
                                
                                status_text.empty()
                                st.success(f"✅ Batch processing complete! Successful: {success_count}, Failed: {fail_count}, Skipped: {skipped_count}")
                            time.sleep(1)
                            st.rerun()

                    st.divider()
                    
                    # Download Report Button for Tab 2
                    if st.button("📥 Download Excel Report", type="primary", key="download_report_tab2"):
                        try:
                            # Fetch all summaries
                            all_summaries = database.get_all_summaries()
                            
                            if all_summaries:
                                # Deduplicate summaries - keep only the latest for each filename
                                latest_summaries = {}
                                for summary in all_summaries:
                                    filename = summary.get('filename')
                                    if filename:
                                        # Since get_all_summaries orders by created_at desc, 
                                        # the first one we see is the latest
                                        if filename not in latest_summaries:
                                            latest_summaries[filename] = summary
                                
                                unique_summaries = list(latest_summaries.values())
                                
                                report_gen = ReportGenerator()
                                excel_file = report_gen.create_summary_report(unique_summaries, pdf_processor.download_folder)
                                
                                with open(excel_file, 'rb') as f:
                                    st.download_button(
                                        label="💾 Click to Download",
                                        data=f,
                                        file_name=excel_file,
                                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                        key="download_excel_btn_tab2"
                                    )
                                
                                # Clean up
                                if os.path.exists(excel_file):
                                    os.remove(excel_file)
                            else:
                                st.warning("No summaries found to export")
                                
                        except Exception as e:
                            st.error(f"Error generating report: {str(e)}")

                    st.divider()

                    # Display each file
                    for idx, filename in enumerate(existing_files, 1):
                        # Check if summary exists in database
                        summary_record = database.get_summary_by_filename(filename)
                        
                        # Determine status icon
                        icon = "⚪"  # Default/Pending
                        if summary_record:
                            status = summary_record.get('status')
                            if status == 'success':
                                icon = "✅"
                            elif status == 'failed':
                                icon = "❌"
                        
                        with st.expander(f"{icon} {idx}. {filename}"):

                            if summary_record and summary_record.get('status') == 'success':
                                st.success("✅ Summary available")

                                st.markdown("**Long Summary:**")
                                st.text_area(
                                    "Long Summary",
                                    value=summary_record.get('long_summary', ''),
                                    height=150,
                                    key=f"existing_long_{idx}",
                                    label_visibility="collapsed"
                                )

                                st.markdown("**Short Summary:**")
                                st.text_area(
                                    "Short Summary",
                                    value=summary_record.get('short_summary', ''),
                                    height=100,
                                    key=f"existing_short_{idx}",
                                    label_visibility="collapsed"
                                )

                                if summary_record.get('url'):
                                    st.markdown(f"**Source URL**: {summary_record['url']}")

                                st.markdown(f"**Created**: {summary_record.get('created_at', 'Unknown')}")

                                # Re-summarize button
                                if st.button(f"🔄 Re-summarize", key=f"resummarize_{idx}"):
                                    if long_prompt and short_prompt:
                                        with st.spinner(f"Re-summarizing {filename}..."):
                                            filepath = os.path.join(pdf_processor.download_folder, filename)
                                            success, extracted_text, error = pdf_processor.extract_text_and_tables(filepath)

                                            if success:
                                                success, long_summary, short_summary, error = summarizer.create_summaries(
                                                    extracted_text, long_prompt, short_prompt
                                                )

                                                if success:
                                                    # Update database
                                                    result = {
                                                        'url': summary_record.get('url', ''),
                                                        'filename': filename,
                                                        'long_summary': long_summary,
                                                        'short_summary': short_summary,
                                                        'status': 'success',
                                                        'error_message': '',
                                                        'created_at': datetime.utcnow().isoformat()
                                                    }
                                                    database.insert_summary(result)
                                                    st.success("✅ Re-summarization complete! Refresh the page to see updates.")
                                                else:
                                                    st.error(f"❌ Summarization failed: {error}")
                                            else:
                                                st.error(f"❌ Text extraction failed: {error}")
                                    else:
                                        st.warning("⚠️ Please set long and short summary prompts first")
                            elif summary_record and summary_record.get('status') == 'failed':
                                st.error(f"❌ Processing Failed: {summary_record.get('error_message', 'Unknown error')}")
                                st.markdown(f"**Attempted**: {summary_record.get('created_at', 'Unknown')}")
                                
                                # Retry button
                                if st.button(f"🔄 Retry", key=f"retry_{idx}"):
                                    if long_prompt and short_prompt:
                                        with st.spinner(f"Retrying {filename}..."):
                                            filepath = os.path.join(pdf_processor.download_folder, filename)
                                            success, extracted_text, error = pdf_processor.extract_text_and_tables(filepath)
                                            
                                            if success:
                                                success, long_summary, short_summary, error = summarizer.create_summaries(
                                                    extracted_text, long_prompt, short_prompt
                                                )
                                                
                                                if success:
                                                    # Update database
                                                    result = {
                                                        'url': summary_record.get('url', ''),
                                                        'filename': filename,
                                                        'long_summary': long_summary,
                                                        'short_summary': short_summary,
                                                        'status': 'success',
                                                        'error_message': '',
                                                        'created_at': datetime.utcnow().isoformat()
                                                    }
                                                    database.insert_summary(result)
                                                    st.success("✅ Retry successful! Refresh the page to see updates.")
                                                    time.sleep(1)
                                                    st.rerun()
                                                else:
                                                    error_msg = f"Retry failed: {error}"
                                                    st.error(error_msg)
                                                    # Update failure in database
                                                    result = {
                                                        'url': summary_record.get('url', ''),
                                                        'filename': filename,
                                                        'long_summary': f"FAILED: {error_msg}",
                                                        'short_summary': f"FAILED: {error_msg}",
                                                        'status': 'failed',
                                                        'error_message': error_msg,
                                                        'created_at': datetime.utcnow().isoformat()
                                                    }
                                                    database.insert_summary(result)
                                            else:
                                                st.error(f"❌ Text extraction failed: {error}")
                                    else:
                                        st.warning("⚠️ Please set long and short summary prompts first")

                            else:
                                st.warning("⚠️ No summary found in database")

                                # Summarize button for files without summaries
                                if st.button(f"🤖 Generate Summary", key=f"summarize_{idx}"):
                                    if long_prompt and short_prompt:
                                        # Try to get existing URL from database
                                        existing_url = ''
                                        existing_summary = database.get_summary_by_filename(filename)
                                        if existing_summary and existing_summary.get('url'):
                                            existing_url = existing_summary.get('url')
                                        
                                        with st.spinner(f"Generating summary for {filename}..."):
                                            filepath = os.path.join(pdf_processor.download_folder, filename)
                                            success, extracted_text, error = pdf_processor.extract_text_and_tables(filepath)

                                            if success:
                                                success, long_summary, short_summary, error = summarizer.create_summaries(
                                                    extracted_text, long_prompt, short_prompt
                                                )

                                                if success:
                                                    # Save to database
                                                    result = {
                                                        'url': existing_url,
                                                        'filename': filename,
                                                        'long_summary': long_summary,
                                                        'short_summary': short_summary,
                                                        'status': 'success',
                                                        'error_message': '',
                                                        'created_at': datetime.utcnow().isoformat()
                                                    }
                                                    database.insert_summary(result)
                                                    st.success("✅ Summarization complete! Refresh the page to see updates.")
                                                else:
                                                    error_msg = f"Summarization failed: {error}"
                                                    st.error(f"❌ {error_msg}")
                                                    # Save failure to database
                                                    result = {
                                                        'url': existing_url,
                                                        'filename': filename,
                                                        'long_summary': f"FAILED: {error_msg}",
                                                        'short_summary': f"FAILED: {error_msg}",
                                                        'status': 'failed',
                                                        'error_message': error_msg,
                                                        'created_at': datetime.utcnow().isoformat()
                                                    }
                                                    database.insert_summary(result)
                                                    time.sleep(1)
                                                    st.rerun()
                                            else:
                                                error_msg = f"Text extraction failed: {error}"
                                                st.error(f"❌ {error_msg}")
                                                # Save failure to database
                                                result = {
                                                    'url': existing_url,
                                                    'filename': filename,
                                                    'long_summary': f"FAILED: {error_msg}",
                                                    'short_summary': f"FAILED: {error_msg}",
                                                    'status': 'failed',
                                                    'error_message': error_msg,
                                                    'created_at': datetime.utcnow().isoformat()
                                                }
                                                database.insert_summary(result)
                                                time.sleep(1)
                                                st.rerun()
                                    else:
                                        st.warning("⚠️ Please set long and short summary prompts first")
                else:
                    st.info("No PDF files found in the files folder")
            else:
                st.error(f"❌ Initialization error: {init_error}")
        else:
            st.warning("⚠️ Please configure API keys and Supabase credentials in .streamlit/secrets.toml to view existing files.")
            if not api_key:
                st.error(f"❌ Missing {ai_provider} API Key")
            if not supabase_url:
                st.error("❌ Missing Supabase URL")
            if not supabase_key:
                st.error("❌ Missing Supabase Key")


def display_status_table(results: List[Dict], pdf_processor, summarizer, database, long_prompt: str, short_prompt: str, key_prefix: str = "", show_summary_status: bool = True):
    """
    Display status table with download and summary status for each file

    Args:
        results: List of result dictionaries
        pdf_processor: PDFProcessor instance
        summarizer: Summarizer instance
        database: SummaryDatabase instance
        long_prompt: Long summary prompt
        short_prompt: Short summary prompt
        key_prefix: Unique prefix for button keys to avoid duplicates
        show_summary_status: Whether to show the summary status column
    """
    if not results:
        return

    # Create status table
    for idx, result in enumerate(results):
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])

            with col1:
                st.write(f"**{idx + 1}. {result.get('filename', 'Unknown')}**")
                if result.get('url'):
                    st.caption(f"{result['url'][:50]}...")

            with col2:
                # Download status
                download_status = result.get('download_status', 'pending')
                if download_status == 'success':
                    st.success("✅ Downloaded")
                elif download_status == 'skipped':
                    st.info("✅ Already Exists")
                elif download_status == 'failed':
                    st.error("❌ Download Failed")
                    if result.get('download_error'):
                        st.caption(result['download_error'][:50])
                # Removed pending/warning status as requested

            # Initialize summary_status to avoid UnboundLocalError
            summary_status = result.get('summary_status', 'pending')

            with col3:
                if show_summary_status:
                    # Summary status
                    # summary_status already initialized above
                    if summary_status == 'success':
                        st.success("✅ Summarized")
                    elif summary_status == 'failed':
                        st.error("❌ Summary Failed")
                        if result.get('summary_error'):
                            st.caption(result['summary_error'][:50])
                    elif summary_status == 'pending':
                        st.warning("⏳ Pending")
                    else:
                        st.info("⏭️ Skipped")

            with col4:
                # View summary button
                if summary_status == 'success':
                    if st.button("👁️ View", key=f"{key_prefix}_view_{idx}"):
                        st.session_state[f'{key_prefix}_show_summary_{idx}'] = not st.session_state.get(f'{key_prefix}_show_summary_{idx}', False)

            with col5:
                # Retry button for failures
                if download_status == 'failed':
                    if st.button("🔄", key=f"{key_prefix}_retry_download_{idx}"):
                        with st.spinner(f"Retrying download for {result.get('filename', 'file')}..."):
                            new_result = download_pdf_file(result['url'], pdf_processor, skip_existing=False)
                            # Update the result in session state
                            st.session_state.file_results[idx] = new_result
                            st.rerun()

                elif summary_status == 'failed':
                    if st.button("🔄", key=f"{key_prefix}_retry_summary_{idx}"):
                        with st.spinner(f"Retrying summarization for {result.get('filename', 'file')}..."):
                            new_result = summarize_pdf(result, summarizer, database, long_prompt, short_prompt)
                            # Update the result in session state
                            st.session_state.file_results[idx] = new_result
                            st.rerun()

            # Show summary details if expanded
            if st.session_state.get(f'{key_prefix}_show_summary_{idx}', False) and summary_status == 'success':
                st.markdown("**Long Summary:**")
                st.text_area(
                    "Long Summary",
                    value=result.get('long_summary', ''),
                    height=150,
                    key=f"{key_prefix}_table_long_{idx}",
                    label_visibility="collapsed"
                )

                st.markdown("**Short Summary:**")
                st.text_area(
                    "Short Summary",
                    value=result.get('short_summary', ''),
                    height=100,
                    key=f"{key_prefix}_table_short_{idx}",
                    label_visibility="collapsed"
                )

            st.divider()


def display_result(result: Dict, index: int):
    """
    Display a single result item

    Args:
        result: Result dictionary
        index: Item index
    """
    if result['status'] == 'success':
        status_icon = "✅"
    elif result['status'] == 'skipped':
        status_icon = "⏭️"
    else:
        status_icon = "❌"

    with st.expander(f"{status_icon} {index}. {result['filename'] or 'Unknown'} - {result['status'].upper()}"):
        st.markdown(f"**URL**: {result['url']}")

        if result['status'] == 'success':
            st.markdown("**Long Summary:**")
            st.text_area(
                "Long Summary",
                value=result['long_summary'],
                height=150,
                key=f"long_{index}",
                label_visibility="collapsed"
            )

            st.markdown("**Short Summary:**")
            st.text_area(
                "Short Summary",
                value=result['short_summary'],
                height=100,
                key=f"short_{index}",
                label_visibility="collapsed"
            )
        elif result['status'] == 'skipped':
            st.info("File already exists and was skipped")
        else:
            st.error(f"**Error**: {result['error_message']}")


if __name__ == "__main__":
    main()
