import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    print("Keyring library not found. Falling back to file-based key storage. This is less secure.")

KEY_FILE_PATH = "supabase_encryption_key.key"
SERVICE_ID = "HomeUnitCalculator_Supabase_Key"
USERNAME = "default_user" # A generic username for keyring

def _generate_key():
    """Generates a new encryption key."""
    return Fernet.generate_key()

def _store_key_securely(key: bytes):
    """Stores the encryption key using keyring or a file."""
    global KEYRING_AVAILABLE # Declare intent to modify the global variable
    if KEYRING_AVAILABLE:
        try:
            keyring.set_password(SERVICE_ID, USERNAME, base64.urlsafe_b64encode(key).decode())
            return True
        except Exception as e:
            print(f"Keyring storage failed: {e}. Falling back to file.")
            KEYRING_AVAILABLE = False # Disable keyring for this session
    
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

def _get_key_securely():
    """Retrieves the encryption key from keyring or a file."""
    key = None
    global KEYRING_AVAILABLE # Declare intent to modify the global variable
    if KEYRING_AVAILABLE:
        try:
            stored_key = keyring.get_password(SERVICE_ID, USERNAME)
            if stored_key:
                key = base64.urlsafe_b64decode(stored_key.encode())
        except Exception as e:
            print(f"Keyring retrieval failed: {e}. Trying file-based key.")
            KEYRING_AVAILABLE = False # Disable keyring for this session

    if key is None and os.path.exists(KEY_FILE_PATH):
        try:
            with open(KEY_FILE_PATH, "rb") as key_file:
                key = key_file.read()
        except Exception as e:
            print(f"File key retrieval failed: {e}")
    
    return key

def get_or_create_key():
    """
    Gets the existing encryption key or creates a new one if it doesn't exist.
    Returns the key as bytes.
    """
    key = _get_key_securely()
    if key is None:
        print("No existing encryption key found. Generating a new one.")
        key = _generate_key()
        if not _store_key_securely(key):
            raise Exception("Failed to store the generated encryption key securely.")
    return key

if __name__ == "__main__":
    # Example usage and testing
    print("Testing key_manager.py...")
    try:
        # Ensure no old key exists for a clean test
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(SERVICE_ID, USERNAME)
                print("Cleared old keyring entry (if any).")
            except keyring.errors.NoPasswordFoundException:
                pass # No password to delete
            except Exception as e:
                print(f"Error clearing keyring: {e}")
        if os.path.exists(KEY_FILE_PATH):
            os.remove(KEY_FILE_PATH)
            print("Removed old key file (if any).")

        # Get or create the key
        my_key = get_or_create_key()
        print(f"Retrieved/Generated Key: {my_key.decode()}")

        # Try to get the key again (should retrieve the same one)
        my_key_again = get_or_create_key()
        print(f"Retrieved Key again: {my_key_again.decode()}")
        assert my_key == my_key_again
        print("Key retrieval successful and consistent.")

        # Clean up for testing purposes
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(SERVICE_ID, USERNAME)
                print("Cleaned up keyring entry.")
            except keyring.errors.NoPasswordFoundException:
                pass
        if os.path.exists(KEY_FILE_PATH):
            os.remove(KEY_FILE_PATH)
            print("Cleaned up key file.")

    except Exception as e:
        print(f"An error occurred during testing: {e}")