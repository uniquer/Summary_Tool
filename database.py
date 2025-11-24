"""
Supabase database integration for storing summary results
"""
from supabase import create_client, Client
from datetime import datetime
from typing import Dict, List, Optional
import os


class SummaryDatabase:
    """Handles all Supabase database operations"""

    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize Supabase client

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
        """
        self.client: Client = create_client(supabase_url, supabase_key)
        self.table_name = "pdf_summaries"

    def create_table_if_not_exists(self):
        """
        Create the summaries table if it doesn't exist
        Note: This is best done via Supabase SQL editor, but included for reference

        SQL to run in Supabase:

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
        """
        pass

    def insert_summary(self, data: Dict) -> Optional[Dict]:
        """
        Insert a new summary record

        Args:
            data: Dictionary containing summary data
                - url: str
                - filename: str
                - long_summary: str
                - short_summary: str
                - status: str (success/failed)
                - error_message: str (optional)

        Returns:
            Inserted record or None if failed
        """
        try:
            record = {
                "url": data.get("url"),
                "filename": data.get("filename"),
                "long_summary": data.get("long_summary", ""),
                "short_summary": data.get("short_summary", ""),
                "status": data.get("status", "pending"),
                "error_message": data.get("error_message", ""),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            response = self.client.table(self.table_name).insert(record).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error inserting summary: {str(e)}")
            return None

    def update_summary(self, record_id: int, data: Dict) -> Optional[Dict]:
        """
        Update an existing summary record

        Args:
            record_id: ID of the record to update
            data: Dictionary containing fields to update

        Returns:
            Updated record or None if failed
        """
        try:
            data["updated_at"] = datetime.utcnow().isoformat()
            response = self.client.table(self.table_name)\
                .update(data)\
                .eq("id", record_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error updating summary: {str(e)}")
            return None

    def get_all_summaries(self) -> List[Dict]:
        """
        Retrieve all summary records

        Returns:
            List of all summary records
        """
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .order("created_at", desc=True)\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching summaries: {str(e)}")
            return []

    def get_summaries_by_session(self, session_start: datetime) -> List[Dict]:
        """
        Get summaries created after a specific time

        Args:
            session_start: Start time for filtering

        Returns:
            List of summary records
        """
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .gte("created_at", session_start.isoformat())\
                .order("created_at", desc=False)\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching session summaries: {str(e)}")
            return []

    def delete_summary(self, record_id: int) -> bool:
        """
        Delete a summary record

        Args:
            record_id: ID of the record to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.table(self.table_name)\
                .delete()\
                .eq("id", record_id)\
                .execute()
            return True
        except Exception as e:
            print(f"Error deleting summary: {str(e)}")
            return False

    def get_summary_by_filename(self, filename: str) -> Optional[Dict]:
        """
        Get the most recent summary for a specific filename

        Args:
            filename: Name of the file to search for

        Returns:
            Summary record or None if not found
        """
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq("filename", filename)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching summary by filename: {str(e)}")
            return None
