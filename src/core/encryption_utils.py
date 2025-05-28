from cryptography.fernet import Fernet
from src.core.key_manager import get_or_create_key

class EncryptionUtil:
    def __init__(self):
        try:
            self.key = get_or_create_key()
            # Validate key format before creating Fernet instance
            if not isinstance(self.key, bytes) or len(self.key) != 44:
                raise ValueError("Invalid key format or length")
            self.f = Fernet(self.key)
        except (ValueError, TypeError, Exception) as e:
            raise RuntimeError(f"Invalid encryption key: {e}")

    def encrypt_data(self, data: str) -> bytes:
        """Encrypts a string and returns bytes."""
        if not isinstance(data, str):
            raise TypeError("Data must be a string")
        if not data:
            raise ValueError("Data cannot be empty")
        try:
            return self.f.encrypt(data.encode())
        except Exception as e:
            raise RuntimeError(f"Encryption failed: {e}")

    def decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypts bytes and returns a string."""
        if not isinstance(encrypted_data, bytes):
            raise TypeError("Encrypted data must be bytes")
        try:
            return self.f.decrypt(encrypted_data).decode()
        except Exception as e:
            raise RuntimeError(f"Decryption failed: {e}")

if __name__ == "__main__":
    # Example usage and testing
    print("Testing encryption_utils.py...")
    try:
        encryptor = EncryptionUtil()

        original_data = "This is a secret Supabase URL and key."
        print(f"Original data: {original_data}")

        encrypted = encryptor.encrypt_data(original_data)
        print(f"Encrypted data: {encrypted}")

        decrypted = encryptor.decrypt_data(encrypted)
        print(f"Decrypted data: {decrypted}")

        assert original_data == decrypted
        print("Encryption and decryption successful!")

        # Test with another piece of data
        another_data = "Another sensitive piece of information."
        encrypted_another = encryptor.encrypt_data(another_data)
        decrypted_another = encryptor.decrypt_data(encrypted_another)
        assert another_data == decrypted_another
        print("Another encryption/decryption test successful.")

        # Test edge cases
        print("Testing edge cases...")
        
        # Test with unicode characters
        unicode_data = "Special chars: éñ中文🔐"
        encrypted_unicode = encryptor.encrypt_data(unicode_data)
        decrypted_unicode = encryptor.decrypt_data(encrypted_unicode)
        assert unicode_data == decrypted_unicode
        print("Unicode test successful.")
        
        # Test error cases
        try:
            encryptor.encrypt_data("")
            assert False, "Should have raised ValueError for empty string"
        except ValueError:
            print("Empty string validation test passed.")
        
        try:
            encryptor.encrypt_data(123)
            assert False, "Should have raised TypeError for non-string"
        except TypeError:
            print("Type validation test passed.")

    except Exception as e:
        print(f"An error occurred during testing: {e}")