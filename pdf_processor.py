"""
PDF download and text extraction module
"""
import requests
import pdfplumber
import os
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse
import re


class PDFProcessor:
    """Handles PDF downloading and text extraction"""

    def __init__(self, download_folder: str = "files"):
        """
        Initialize PDF processor

        Args:
            download_folder: Folder to store downloaded PDFs
        """
        self.download_folder = download_folder
        self._ensure_folder_exists()

    def _ensure_folder_exists(self):
        """Create download folder if it doesn't exist"""
        Path(self.download_folder).mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing invalid characters

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:196] + ext
        return filename

    def _get_filename_from_url(self, url: str) -> str:
        """
        Extract filename from URL

        Args:
            url: PDF URL

        Returns:
            Filename
        """
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)

        # If no filename in URL, generate one
        if not filename or not filename.endswith('.pdf'):
            filename = f"document_{hash(url) % 100000}.pdf"

        return self._sanitize_filename(filename)

    def download_pdf(self, url: str, custom_filename: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Download PDF from URL

        Args:
            url: PDF file URL
            custom_filename: Optional custom filename

        Returns:
            Tuple of (success: bool, filepath: str, error_message: str)
        """
        try:
            # Get filename
            if custom_filename:
                filename = self._sanitize_filename(custom_filename)
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
            else:
                filename = self._get_filename_from_url(url)

            filepath = os.path.join(self.download_folder, filename)

            # Download with timeout
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Check if content is PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower():
                return False, "", f"URL does not point to a PDF file (Content-Type: {content_type})"

            # Write to file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True, filepath, ""

        except requests.exceptions.Timeout:
            return False, "", "Download timeout (30 seconds exceeded)"
        except requests.exceptions.HTTPError as e:
            return False, "", f"HTTP error: {e.response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, "", f"Download error: {str(e)}"
        except Exception as e:
            return False, "", f"Unexpected error: {str(e)}"

    def extract_text_and_tables(self, filepath: str) -> Tuple[bool, str, str]:
        """
        Extract text and tables from PDF

        Args:
            filepath: Path to PDF file

        Returns:
            Tuple of (success: bool, extracted_text: str, error_message: str)
        """
        try:
            extracted_content = []

            with pdfplumber.open(filepath) as pdf:
                total_pages = len(pdf.pages)

                # Limit pages for very large PDFs
                max_pages = min(total_pages, 100)  # Process max 100 pages

                for page_num, page in enumerate(pdf.pages[:max_pages], 1):
                    # Extract text
                    text = page.extract_text()
                    if text:
                        extracted_content.append(f"\n--- Page {page_num} ---\n")
                        extracted_content.append(text)

                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables, 1):
                            extracted_content.append(f"\n[Table {table_idx} on Page {page_num}]\n")
                            # Convert table to text format
                            for row in table:
                                row_text = " | ".join([str(cell) if cell else "" for cell in row])
                                extracted_content.append(row_text)
                            extracted_content.append("")

                if total_pages > max_pages:
                    extracted_content.append(f"\n[Note: Only first {max_pages} pages processed out of {total_pages} total pages]")

            full_text = "\n".join(extracted_content)

            if not full_text.strip():
                return False, "", "No text content extracted from PDF"

            return True, full_text, ""

        except Exception as e:
            return False, "", f"PDF extraction error: {str(e)}"

    def process_pdf(self, url: str) -> Tuple[bool, str, str, str]:
        """
        Download and extract text from PDF in one step

        Args:
            url: PDF URL

        Returns:
            Tuple of (success: bool, filename: str, extracted_text: str, error_message: str)
        """
        # Download
        success, filepath, error = self.download_pdf(url)
        if not success:
            return False, "", "", error

        filename = os.path.basename(filepath)

        # Extract text
        success, text, error = self.extract_text_and_tables(filepath)
        if not success:
            return False, filename, "", error

        return True, filename, text, ""

    def delete_file(self, filename: str) -> bool:
        """
        Delete a downloaded PDF file

        Args:
            filename: Name of file to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = os.path.join(self.download_folder, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
            return False

    def list_all_files(self) -> list:
        """
        List all PDF files in the download folder

        Returns:
            List of PDF filenames
        """
        try:
            if not os.path.exists(self.download_folder):
                return []
            files = [f for f in os.listdir(self.download_folder) if f.endswith('.pdf')]
            return sorted(files)
        except Exception as e:
            print(f"Error listing files: {str(e)}")
            return []

    def file_exists(self, filename: str) -> bool:
        """
        Check if a file exists in the download folder

        Args:
            filename: Name of file to check

        Returns:
            True if file exists, False otherwise
        """
        filepath = os.path.join(self.download_folder, filename)
        return os.path.exists(filepath)

    def get_expected_filename(self, url: str) -> str:
        """
        Get the expected filename for a URL without downloading

        Args:
            url: PDF URL

        Returns:
            Expected filename
        """
        return self._get_filename_from_url(url)
