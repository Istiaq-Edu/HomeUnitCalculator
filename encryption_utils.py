from cryptography.fernet import Fernet
from key_manager import get_or_create_key

class EncryptionUtil:
    def __init__(self):
        self.key = get_or_create_key()
        self.f = Fernet(self.key)

    def encrypt_data(self, data: str) -> bytes:
        """Encrypts a string and returns bytes."""
        return self.f.encrypt(data.encode())

    def decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypts bytes and returns a string."""
        return self.f.decrypt(encrypted_data).decode()

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

    except Exception as e:
        print(f"An error occurred during testing: {e}")