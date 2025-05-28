import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

try:
    import keyring
    _KEYRING_INITIAL_AVAILABLE = True # Use a private global for initial check
except ImportError:
    _KEYRING_INITIAL_AVAILABLE = False
    print("Keyring library not found. Falling back to file-based key storage. This is less secure.")

KEY_FILE_PATH = "supabase_encryption_key.key"
SERVICE_ID = "HomeUnitCalculator_Supabase_Key"
USERNAME = "default_user" # A generic username for keyring

class KeyManager:
    def __init__(self):
        self.keyring_available = _KEYRING_INITIAL_AVAILABLE
    
    def _generate_key(self):
        """Generates a new encryption key."""
        return Fernet.generate_key()

    def _store_key_securely(self, key: bytes):
        """Stores the encryption key using keyring or a file."""
        if self.keyring_available:
            try:
                keyring.set_password(SERVICE_ID, USERNAME, key.decode())
                return True
            except Exception as e:
                print(f"Keyring storage failed: {e}. Falling back to file.")
                self.keyring_available = False # Disable keyring for this instance
        
        # Fallback to file storage if keyring is not available or failed
        try:
            with open(KEY_FILE_PATH, "wb") as key_file:
                key_file.write(key)
            # Set restrictive permissions for the key file (Unix-like systems)
            if os.name == 'posix':
                os.chmod(KEY_FILE_PATH, 0o600) # Owner read/write only
            return True
        except Exception as e:
            print(f"File storage failed: {e}")
            return False

    def _get_key_securely(self):
        """Retrieves the encryption key from keyring or a file."""
        key = None
        if self.keyring_available:
            try:
                stored_key = keyring.get_password(SERVICE_ID, USERNAME)
                if stored_key:
                    key = stored_key.encode()
            except Exception as e:
                print(f"Keyring retrieval failed: {e}. Trying file-based key.")
                self.keyring_available = False # Disable keyring for this instance

        if key is None and os.path.exists(KEY_FILE_PATH):
            try:
                with open(KEY_FILE_PATH, "rb") as key_file:
                    key = key_file.read()
            except Exception as e:
                print(f"File key retrieval failed: {e}")
        
        return key

    def _delete_key_securely(self):
        """Deletes the encryption key from keyring and file."""
        if self.keyring_available:
            try:
                keyring.delete_password(SERVICE_ID, USERNAME)
                print("Deleted key from keyring.")
            except keyring.errors.PasswordDeleteError:
                pass # No password to delete
            except Exception as e:
                print(f"Error deleting key from keyring: {e}")
        
        if os.path.exists(KEY_FILE_PATH):
            try:
                os.remove(KEY_FILE_PATH)
                print("Deleted key file.")
            except Exception as e:
                print(f"Error deleting key file: {e}")

    def get_or_create_key(self):
        """
        Gets the existing encryption key or creates a new one if it doesn't exist.
        Returns the key as bytes.
        """
        key = self._get_key_securely()
        
        if key is not None:
            try:
                Fernet(key) # Validate existing key
            except ValueError as e:
                print(f"Invalid encryption key retrieved: {e}. Deleting and regenerating key.")
                self._delete_key_securely() # Delete the invalid key
                key = None # Force regeneration

        if key is None:
            print("No valid encryption key found. Generating a new one.")
            key = self._generate_key()
            if not self._store_key_securely(key):
                raise Exception("Failed to store the generated encryption key securely.")
        
        return key

# Global instance for backward compatibility with existing calls
_key_manager_instance = KeyManager()

def get_or_create_key():
    """
    Public function to get or create the key, using the singleton KeyManager instance.
    This maintains compatibility with existing code that calls get_or_create_key() directly.
    """
    return _key_manager_instance.get_or_create_key()

if __name__ == "__main__":
    # Example usage and testing
    print("Testing key_manager.py...")
    test_key_manager = KeyManager() # Use a separate instance for testing to avoid interfering with global
    try:
        # Ensure no old key exists for a clean test
        if test_key_manager.keyring_available:
            try:
                keyring.delete_password(SERVICE_ID, USERNAME)
                print("Cleared old keyring entry (if any).")
            except keyring.errors.PasswordDeleteError:
                pass # No password to delete
            except keyring.errors.KeyringError as e: # Catch broader keyring errors
                print(f"A keyring error occurred during deletion: {e}")
            except Exception as e:
                print(f"An unexpected error occurred during keyring deletion: {e}")
        if os.path.exists(KEY_FILE_PATH):
            os.remove(KEY_FILE_PATH)
            print("Removed old key file (if any).")

        # Get or create the key
        my_key = test_key_manager.get_or_create_key()
        print(f"Retrieved/Generated Key: {my_key.decode()}")

        # Try to get the key again (should retrieve the same one)
        my_key_again = test_key_manager.get_or_create_key()
        print(f"Retrieved Key again: {my_key_again.decode()}")
        assert my_key == my_key_again
        print("Key retrieval successful and consistent.")

        # Clean up for testing purposes
        if test_key_manager.keyring_available:
            try:
                keyring.delete_password(SERVICE_ID, USERNAME)
                print("Cleaned up keyring entry.")
            except keyring.errors.PasswordDeleteError:
                pass
            except keyring.errors.KeyringError: # Catch broader keyring errors
                pass # Ignore if already deleted or other keyring error during cleanup
        if os.path.exists(KEY_FILE_PATH):
            os.remove(KEY_FILE_PATH)
            print("Cleaned up key file.")

    except Exception as e:
        print(f"An error occurred during testing: {e}")