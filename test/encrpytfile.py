from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes

class CryptoBase:
    def generate_key_pair(self):
        key = RSA.generate(2048)  # Generate 2048-bit RSA key pair
        return key

    def save_key_to_file(self, key, filename):
        with open(filename, 'wb') as file:
            file.write(key.export_key(format='DER'))

    def load_key_from_file(self, filename):
        with open(filename, 'rb') as file:
            key = RSA.import_key(file.read())
        return key

    def generate_aes_key(self):
        return get_random_bytes(16)  # 128-bit AES key

class Encryption(CryptoBase):
    def encrypt_file(self, input_filename, output_filename, public_key):
        # Generate a random AES key
        aes_key = self.generate_aes_key()

        # Encrypt the file using AES
        aes_cipher = AES.new(aes_key, AES.MODE_EAX)
        with open(input_filename, 'rb') as file:
            data = file.read()
        encrypted_data, tag = aes_cipher.encrypt_and_digest(data)

        # Encrypt the AES key with RSA
        rsa_cipher = PKCS1_OAEP.new(public_key)
        encrypted_aes_key = rsa_cipher.encrypt(aes_key)

        # Write encrypted AES key and data to output file
        with open(output_filename, 'wb') as file:
            file.write(encrypted_aes_key)
            file.write(aes_cipher.nonce)
            file.write(tag)
            file.write(encrypted_data)

class Decryption(CryptoBase):
    def decrypt_file(self, input_filename, output_filename, private_key):
        # Read encrypted AES key, nonce, tag, and data from input file
        with open(input_filename, 'rb') as file:
            encrypted_aes_key = file.read(256)  # RSA encrypted AES key is 256 bytes
            nonce = file.read(16)
            tag = file.read(16)
            encrypted_data = file.read()

        # Decrypt AES key with RSA
        rsa_cipher = PKCS1_OAEP.new(private_key)
        aes_key = rsa_cipher.decrypt(encrypted_aes_key)

        # Decrypt the data using AES
        aes_cipher = AES.new(aes_key, AES.MODE_EAX, nonce=nonce)
        decrypted_data = aes_cipher.decrypt_and_verify(encrypted_data, tag)

        # Write decrypted data to output file
        with open(output_filename, 'wb') as file:
            file.write(decrypted_data)

# Example usage
encryption_instance = Encryption()
decryption_instance = Decryption()

# Generate RSA key pair
key_pair = encryption_instance.generate_key_pair()
public_key = key_pair.publickey()
private_key = key_pair

# Save keys to files in DER format
encryption_instance.save_key_to_file(public_key, 'public_key.der')
encryption_instance.save_key_to_file(private_key, 'private_key.der')

# Load keys from files
public_key = encryption_instance.load_key_from_file('public_key.der')
private_key = encryption_instance.load_key_from_file('private_key.der')

# Encrypt a file
encryption_instance.encrypt_file('Test.png', 'encrypted_file.bin', public_key)

# Decrypt the file
decryption_instance.decrypt_file('encrypted_file.bin', 'decrypted_file.png', private_key)
