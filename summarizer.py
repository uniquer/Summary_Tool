"""
AI-powered summarization module supporting Claude and OpenAI
"""
from anthropic import Anthropic
from openai import OpenAI
from typing import Tuple, Optional
import time


class Summarizer:
    """Handles text summarization using Claude or OpenAI"""

    def __init__(self, provider: str, api_key: str):
        """
        Initialize summarizer with chosen provider

        Args:
            provider: 'claude' or 'openai'
            api_key: API key for the chosen provider
        """
        self.provider = provider.lower()
        self.api_key = api_key

        try:
            if self.provider == 'claude':
                # Initialize Anthropic client with increased timeout for long PDFs
                self.client = Anthropic(
                    api_key=api_key,
                    max_retries=3,
                    timeout=600.0  # 10 minutes to handle long PDF summarization
                )
                self.model = "claude-sonnet-4-5-20250929" #"claude-3-5-sonnet-20241022"
            elif self.provider == 'openai':
                # Initialize OpenAI client with increased timeout for long PDFs
                self.client = OpenAI(
                    api_key=api_key,
                    max_retries=3,
                    timeout=600.0  # 10 minutes to handle long PDF summarization
                )
                self.model = "gpt-4-turbo"
            elif self.provider == 'openrouter':
                # Initialize OpenAI client for OpenRouter
                self.client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key,
                    max_retries=3,
                    timeout=600.0
                )
                self.model = "x-ai/grok-4.1-fast"
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        except Exception as e:
            raise ValueError(f"Failed to initialize {provider} client: {str(e)}")

    def _chunk_text(self, text: str, max_chars: int = 100000) -> list:
        """
        Split text into chunks if it's too long

        Args:
            text: Text to chunk
            max_chars: Maximum characters per chunk

        Returns:
            List of text chunks
        """
        if len(text) <= max_chars:
            return [text]

        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > max_chars:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _summarize_with_claude(self, text: str, prompt: str) -> Tuple[bool, str, str]:
        """
        Summarize text using Claude

        Args:
            text: Text to summarize
            prompt: User's prompt for summarization

        Returns:
            Tuple of (success: bool, summary: str, error_message: str)
        """
        try:
            # Construct the full prompt
            full_prompt = f"""{prompt}

Here is the document to summarize:

{text}

Please provide the summary based on the instructions above."""

            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            )

            summary = message.content[0].text
            return True, summary, ""

        except Exception as e:
            return False, "", f"Claude API error: {str(e)}"

    def _summarize_with_openai(self, text: str, prompt: str) -> Tuple[bool, str, str]:
        """
        Summarize text using OpenAI

        Args:
            text: Text to summarize
            prompt: User's prompt for summarization

        Returns:
            Tuple of (success: bool, summary: str, error_message: str)
        """
        try:
            # Construct the full prompt
            full_prompt = f"""{prompt}

Here is the document to summarize:

{text}

Please provide the summary based on the instructions above."""

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates accurate and concise summaries."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                max_tokens=4096,
                temperature=0.3
            )

            summary = response.choices[0].message.content
            return True, summary, ""

        except Exception as e:
            return False, "", f"OpenAI API error: {str(e)}"

    def _summarize_with_openrouter(self, text: str, prompt: str) -> Tuple[bool, str, str]:
        """
        Summarize text using OpenRouter (Grok)

        Args:
            text: Text to summarize
            prompt: User's prompt for summarization

        Returns:
            Tuple of (success: bool, summary: str, error_message: str)
        """
        try:
            # Construct the full prompt
            full_prompt = f"""{prompt}

Here is the document to summarize:

{text}

Please provide the summary based on the instructions above."""

            # Call OpenRouter API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates accurate and concise summaries."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                extra_body={"reasoning": {"enabled": True}},
                max_tokens=4096,
                temperature=0.3
            )

            summary = response.choices[0].message.content
            return True, summary, ""

        except Exception as e:
            return False, "", f"OpenRouter API error: {str(e)}"

    def summarize(self, text: str, prompt: str) -> Tuple[bool, str, str]:
        """
        Summarize text using the configured provider

        Args:
            text: Text to summarize
            prompt: User's prompt for summarization

        Returns:
            Tuple of (success: bool, summary: str, error_message: str)
        """
        # Handle very long texts by chunking
        chunks = self._chunk_text(text, max_chars=100000)

        if len(chunks) == 1:
            # Single chunk, process normally
            if self.provider == 'claude':
                return self._summarize_with_claude(text, prompt)
            elif self.provider == 'openrouter':
                return self._summarize_with_openrouter(text, prompt)
            else:
                return self._summarize_with_openai(text, prompt)
        else:
            # Multiple chunks - summarize each and combine
            summaries = []

            for i, chunk in enumerate(chunks, 1):
                chunk_prompt = f"{prompt}\n\n(This is part {i} of {len(chunks)} of the document)"

                if self.provider == 'claude':
                    success, summary, error = self._summarize_with_claude(chunk, chunk_prompt)
                elif self.provider == 'openrouter':
                    success, summary, error = self._summarize_with_openrouter(chunk, chunk_prompt)
                else:
                    success, summary, error = self._summarize_with_openai(chunk, chunk_prompt)

                if not success:
                    return False, "", f"Error in chunk {i}: {error}"

                summaries.append(f"[Part {i}]\n{summary}")

            # Combine all chunk summaries
            combined_summary = "\n\n".join(summaries)

            # If there are many chunks, create a final summary of summaries
            if len(chunks) > 3:
                final_prompt = f"{prompt}\n\nPlease create a final consolidated summary from these partial summaries:"

                if self.provider == 'claude':
                    return self._summarize_with_claude(combined_summary, final_prompt)
                elif self.provider == 'openrouter':
                    return self._summarize_with_openrouter(combined_summary, final_prompt)
                else:
                    return self._summarize_with_openai(combined_summary, final_prompt)

            return True, combined_summary, ""

    def create_summaries(self, text: str, long_prompt: str, short_prompt: str) -> Tuple[bool, str, str, str]:
        """
        Create both long and short summaries

        Args:
            text: Text to summarize
            long_prompt: Prompt for long summary
            short_prompt: Prompt for short summary

        Returns:
            Tuple of (success: bool, long_summary: str, short_summary: str, error_message: str)
        """
        # Generate long summary
        success, long_summary, error = self.summarize(text, long_prompt)
        if not success:
            return False, "", "", f"Long summary error: {error}"

        # Wait a bit to respect rate limits
        time.sleep(2)

        # Generate short summary using the long summary as context
        # This significantly reduces token usage as we don't send the full text again
        short_summary_context = f"Here is a detailed summary of a document. Please generate a very concise short summary based on this:\n\n{long_summary}"
        success, short_summary, error = self.summarize(short_summary_context, short_prompt)
        
        if not success:
            # If short summary fails, we still return the long summary
            return False, long_summary, "", f"Short summary error: {error}"

        return True, long_summary, short_summary, ""
