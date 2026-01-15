"""
Supabase Error Handler - Detects and handles common Supabase errors.

This module provides user-friendly error messages for common Supabase issues,
especially for free tier users where projects get paused after inactivity.
"""

import logging
from typing import Optional, Tuple
from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap


class SupabaseErrorType:
    """Enum-like class for Supabase error types."""
    PAUSED_PROJECT = "paused_project"
    CONNECTION_TIMEOUT = "connection_timeout"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class SupabaseErrorHandler:
    """
    Handles Supabase errors and provides user-friendly messages.
    
    Detects common issues like:
    - Paused projects (free tier)
    - Connection timeouts
    - Authentication errors
    - Rate limiting
    - Network issues
    """
    
    # Common error patterns for paused projects
    PAUSED_PROJECT_INDICATORS = [
        "connection refused",
        "connection reset",
        "connection timed out",
        "name resolution error",
        "getaddrinfo failed",
        "no route to host",
        "network is unreachable",
        "connection aborted",
        "bad gateway",
        "service unavailable",
        "502",
        "503",
        "504",
    ]
    
    # Timeout indicators
    TIMEOUT_INDICATORS = [
        "timeout",
        "timed out",
        "read timeout",
        "connect timeout",
    ]
    
    # Authentication indicators
    AUTH_INDICATORS = [
        "unauthorized",
        "401",
        "403",
        "forbidden",
        "invalid api key",
        "invalid token",
    ]
    
    # Rate limit indicators
    RATE_LIMIT_INDICATORS = [
        "rate limit",
        "too many requests",
        "429",
    ]
    
    @staticmethod
    def detect_error_type(error: Exception) -> str:
        """
        Detect the type of Supabase error.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Error type string (from SupabaseErrorType)
        """
        error_str = str(error).lower()
        
        # Check for paused project (most common for free tier)
        if any(indicator in error_str for indicator in SupabaseErrorHandler.PAUSED_PROJECT_INDICATORS):
            return SupabaseErrorType.PAUSED_PROJECT
        
        # Check for timeout
        if any(indicator in error_str for indicator in SupabaseErrorHandler.TIMEOUT_INDICATORS):
            return SupabaseErrorType.CONNECTION_TIMEOUT
        
        # Check for authentication
        if any(indicator in error_str for indicator in SupabaseErrorHandler.AUTH_INDICATORS):
            return SupabaseErrorType.AUTHENTICATION_ERROR
        
        # Check for rate limit
        if any(indicator in error_str for indicator in SupabaseErrorHandler.RATE_LIMIT_INDICATORS):
            return SupabaseErrorType.RATE_LIMIT
        
        # Check for general network error
        if (
            "network" in error_str
            or "connection" in error_str
            or "server disconnected" in error_str
            or "disconnected" in error_str
            or "connection reset" in error_str
        ):
            return SupabaseErrorType.NETWORK_ERROR
        
        return SupabaseErrorType.UNKNOWN
    
    @staticmethod
    def get_error_message(error_type: str, supabase_url: Optional[str] = None) -> Tuple[str, str, str]:
        """
        Get user-friendly error message for the error type.
        
        Args:
            error_type: Type of error (from SupabaseErrorType)
            supabase_url: Optional Supabase project URL
            
        Returns:
            Tuple of (title, message, icon_type)
        """
        if error_type == SupabaseErrorType.PAUSED_PROJECT:
            title = "Supabase Project Paused"
            
            # Extract project ID from URL if available
            project_id = None
            if supabase_url:
                try:
                    # URL format: https://xxxxx.supabase.co
                    project_id = supabase_url.split("//")[1].split(".")[0]
                except:
                    pass
            
            message = (
                "⏸️ Your Supabase project appears to be paused.\n\n"
                "This is common with the free tier after 7 days of inactivity.\n\n"
                "📋 To resume your project:\n"
                "1. Go to: https://supabase.com/dashboard/projects\n"
            )
            
            if project_id:
                message += f"2. Find your project: {project_id}\n"
            else:
                message += "2. Find your project in the list\n"
            
            message += (
                "3. Click 'Resume Project' or 'Restore'\n"
                "4. Wait 1-2 minutes for the project to wake up\n"
                "5. Try loading data again\n\n"
                "💡 Tip: Projects auto-pause after 7 days of inactivity on free tier.\n"
                "   Use your app regularly to keep it active!"
            )
            
            return (title, message, "warning")
        
        elif error_type == SupabaseErrorType.CONNECTION_TIMEOUT:
            title = "Connection Timeout"
            message = (
                "⏱️ Connection to Supabase timed out.\n\n"
                "Possible causes:\n"
                "• Your internet connection is slow\n"
                "• Supabase servers are slow to respond\n"
                "• Your project might be paused (free tier)\n\n"
                "💡 Try:\n"
                "1. Check your internet connection\n"
                "2. Wait a moment and try again\n"
                "3. If it persists, check if your project is paused:\n"
                "   https://supabase.com/dashboard/projects"
            )
            return (title, message, "warning")
        
        elif error_type == SupabaseErrorType.AUTHENTICATION_ERROR:
            title = "Authentication Error"
            message = (
                "🔐 Failed to authenticate with Supabase.\n\n"
                "Possible causes:\n"
                "• Invalid API key\n"
                "• Expired credentials\n"
                "• Project settings changed\n\n"
                "💡 Try:\n"
                "1. Go to Supabase Config tab\n"
                "2. Verify your API key is correct\n"
                "3. Get a fresh API key from:\n"
                "   https://supabase.com/dashboard/project/_/settings/api"
            )
            return (title, message, "critical")
        
        elif error_type == SupabaseErrorType.RATE_LIMIT:
            title = "Rate Limit Exceeded"
            message = (
                "🚦 Too many requests to Supabase.\n\n"
                "Free tier has rate limits:\n"
                "• 100 requests per minute\n"
                "• 10,000 requests per day\n\n"
                "💡 Try:\n"
                "1. Wait a minute and try again\n"
                "2. Reduce frequency of requests\n"
                "3. Consider upgrading to Pro tier for higher limits"
            )
            return (title, message, "warning")
        
        elif error_type == SupabaseErrorType.NETWORK_ERROR:
            title = "Network Error"
            message = (
                "🌐 Network connection error.\n\n"
                "Possible causes:\n"
                "• No internet connection\n"
                "• Firewall blocking Supabase\n"
                "• DNS issues\n\n"
                "💡 Try:\n"
                "1. Check your internet connection\n"
                "2. Try accessing https://supabase.com in browser\n"
                "3. Check firewall settings\n"
                "4. Try again in a moment"
            )
            return (title, message, "warning")
        
        else:  # UNKNOWN
            title = "Supabase Error"
            message = (
                "❌ An error occurred while connecting to Supabase.\n\n"
                "💡 Try:\n"
                "1. Check your internet connection\n"
                "2. Verify your project is active:\n"
                "   https://supabase.com/dashboard/projects\n"
                "3. Check Supabase Config tab for correct settings\n"
                "4. Try again in a moment"
            )
            return (title, message, "critical")
    
    @staticmethod
    def show_error_dialog(
        parent: Optional[QWidget],
        error: Exception,
        supabase_url: Optional[str] = None,
        operation: str = "loading data"
    ) -> None:
        """
        Show a user-friendly error dialog for Supabase errors.
        
        Args:
            parent: Parent widget for the dialog
            error: The exception that occurred
            supabase_url: Optional Supabase project URL
            operation: Description of what operation failed (e.g., "loading data")
        """
        # Detect error type
        error_type = SupabaseErrorHandler.detect_error_type(error)
        
        # Log the error
        logging.error(f"Supabase error during {operation}: {error_type} - {error}")
        
        # Get user-friendly message
        title, message, icon_type = SupabaseErrorHandler.get_error_message(error_type, supabase_url)
        
        # Add operation context
        message = f"Failed while {operation}.\n\n" + message
        
        # Show appropriate dialog
        if icon_type == "warning":
            QMessageBox.warning(parent, title, message)
        elif icon_type == "critical":
            QMessageBox.critical(parent, title, message)
        else:
            QMessageBox.information(parent, title, message)
    
    @staticmethod
    def handle_supabase_error(
        error: Exception,
        parent: Optional[QWidget] = None,
        supabase_url: Optional[str] = None,
        operation: str = "loading data",
        show_dialog: bool = True
    ) -> str:
        """
        Handle a Supabase error and optionally show a dialog.
        
        Args:
            error: The exception that occurred
            parent: Parent widget for the dialog
            supabase_url: Optional Supabase project URL
            operation: Description of what operation failed
            show_dialog: Whether to show error dialog (default: True)
            
        Returns:
            Error type string (from SupabaseErrorType)
        """
        error_type = SupabaseErrorHandler.detect_error_type(error)
        
        if show_dialog:
            SupabaseErrorHandler.show_error_dialog(parent, error, supabase_url, operation)
        
        return error_type
    
    @staticmethod
    def is_paused_project_error(error: Exception) -> bool:
        """
        Quick check if error is likely a paused project.
        
        Args:
            error: The exception to check
            
        Returns:
            True if error indicates paused project
        """
        return SupabaseErrorHandler.detect_error_type(error) == SupabaseErrorType.PAUSED_PROJECT


# Convenience function for quick error handling
def handle_supabase_error(
    error: Exception,
    parent: Optional[QWidget] = None,
    supabase_url: Optional[str] = None,
    operation: str = "loading data"
) -> str:
    """
    Convenience function to handle Supabase errors.
    
    Usage:
        try:
            data = supabase_manager.get_rental_records()
        except Exception as e:
            handle_supabase_error(e, self, supabase_url, "loading rental records")
    """
    return SupabaseErrorHandler.handle_supabase_error(error, parent, supabase_url, operation)
