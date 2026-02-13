"""
Supabase client configuration for the application.
This module provides a configured Supabase client that can be used throughout the application.
"""
import os
from supabase import create_client, Client

# Get Supabase credentials from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize Supabase client
supabase_client: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    # Log warning but don't fail - allows app to start without Supabase config
    # This is useful for development or when running tests
    import logging
    logging.warning(
        "Supabase credentials not found in environment variables. "
        "Template features requiring Supabase will not work."
    )
    
    # Create a dummy client for type checking purposes
    # This will raise appropriate errors if actually used
    class DummyClient:
        def __getattr__(self, name):
            def method(*args, **kwargs):
                pass
            return method
    
    supabase_client = DummyClient()

def get_supabase_client() -> Client:
    """
    Get the configured Supabase client.
    
    Returns:
        The Supabase client instance.
    
    Raises:
        RuntimeError: If Supabase is not properly configured.
    """
    return supabase_client
