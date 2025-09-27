import random
from pydub import AudioSegment
import magic
import numpy as np

def get_mime_type(bytes_data):
    return magic.from_buffer(bytes(bytes_data), mime=True)

def get_extension_from_mime(mime_type):
    MIME_TO_EXT = {
        'audio/mpeg': '.mp3',
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'application/pdf': '.pdf',
        'application/zip': '.zip',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'text/plain': '.txt',
        'text/html': '.html',
        'application/json': '.json',
        'application/xml': '.xml',
        'video/mp4': '.mp4'
    }
    return MIME_TO_EXT.get(mime_type, '.bin') 

# Preprocess message file to bits with metadata
def preprocess_message_metadata(filepath, max_message, is_encrypt=False, key="", is_random=False, n_LSB=1):
    with open(filepath, "rb") as f:
        content = f.read()

    # Check size
    if (( len(content)*8 + max_message.bit_length()) > max_message ):
        raise ValueError("Message size exceeds maximum capacity of the audio")
    
    # Optional encryption
    if ( is_encrypt and key ):
        content = encrypt_vigenere(content.decode('latin1'), key).encode('latin1')
    bits = ''.join(format(byte, '08b') for byte in content)

    # Bits for file size info
    message_len = format(len(bits), '08b')
    len_bits = message_len.rjust(max_message.bit_length(), '0')

    return format(n_LSB-1, '02b')+str(is_encrypt&1)+str(is_random&1)+len_bits, bits

def get_message_bytes(bits, is_encrypt=False, key=""):
    message_bytes = bytearray()
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8:
            break
        message_bytes.append(int(byte, 2))
    

    if is_encrypt and key:
        message_bytes = decrypt_vigenere(message_bytes.decode('latin1'), key).encode('latin1')

    return message_bytes

# Auto key Vigenere cipher
# Plaintext is bytes and returns ciphertext bytes
def encrypt_vigenere(plaintext, key):
    if (key == ""):
        return plaintext
    ciphertext = []
    if len(key) < len(plaintext):
        key = key + plaintext

    for i, char in enumerate(plaintext):
        p = ord(char)
        k = ord(key[i])
        c = (p + k) % 256
        ciphertext.append(chr(c))
    return ''.join(ciphertext)

# Ciphertext is bytes and returns plaintext bytes
def decrypt_vigenere(ciphertext, key):
    if (key == ""):
        return ciphertext
    plaintext = []
    for i, char in enumerate(ciphertext):
        c = ord(char)
        k = ord(key[i])
        p = (c - k) % 256
        plaintext.append(chr(p))
        key += chr(p)  # Auto key extension
    return ''.join(plaintext)

def embed_message(audio_path, message_path, is_encrypt=False, key="", is_random=False, n_LSB=1):
    # Load audio & Decoding
    audio = AudioSegment.from_mp3(audio_path)
    raw = audio.raw_data
    channels = audio.channels
    sample_width = audio.sample_width
    frame_rate = audio.frame_rate

    if sample_width != 2:
        raise ValueError("Only 16-bit PCM is supported")
    
    # Normalization & Scaling
    samples = np.frombuffer(raw, dtype=np.int16)
    norm = samples.astype(np.float32) / (2**15) 
    scaled = (norm * 1e6).astype(int)
    max_message = 4*len(scaled)

    # Preprocess message
    message_len, message_bits = preprocess_message_metadata(message_path, max_message, is_encrypt, key, is_random, n_LSB)
    padding_bit = 4 # 2 bits for n_LSB, 1 bit for is_encrypt, 1 bit for is_random

    # Embedding message_len bits
    stego_scaled = scaled.copy()
    n = n_LSB - 1
    i = 0
    for bit in message_len:
        if bit == '0':
            stego_scaled[i] = (stego_scaled[i] & ~(1 << n))
        else:
            stego_scaled[i] = (stego_scaled[i] | (1 << n))

        if (n == 0):
            i += 1
            n = n_LSB - 1
        else:
            n -= 1

    # Embedding message bits
    n = n_LSB - 1 if is_random else n
    i = generate_rand_index(key, len(message_len), int(message_len[padding_bit:], 2), n_LSB, len(scaled)) if is_random else i
    for bit in message_bits:
        if bit == '0':
            stego_scaled[i] = (stego_scaled[i] & ~(1 << n))
        else:
            stego_scaled[i] = (stego_scaled[i] | (1 << n))

        if (n == 0):
            i += 1
            n = n_LSB - 1
        else:
            n -= 1

    # Descaling & Denormalization
    stego_norm = stego_scaled.astype(np.float32) / 1e6
    stego_pcm = (stego_norm * (2**15)).astype(np.int16)

    # Encode to MP3
    stego_audio = AudioSegment(
        data=stego_pcm.tobytes(),
        sample_width=2,
        frame_rate=frame_rate,
        channels=channels
    )
    stego_bytes = stego_audio.export(format="mp3").read()

    return stego_bytes


def extract_message(stego_path, key=""):
    # Load stego audio & Decoding
    audio = AudioSegment.from_mp3(stego_path)
    raw = audio.raw_data
    sample_width = audio.sample_width

    if sample_width != 2:
        raise ValueError("Only 16-bit PCM is supported")

    # Normalization & Scaling
    samples = np.frombuffer(raw, dtype=np.int16)
    norm = samples.astype(np.float32) / (2**15)
    scaled = (norm * 1e6).astype(int)
    max_message = 4*len(scaled)

    bits = ''
    i = -1
    # Get message length bits
    while (i < len(scaled)):
        i += 1
        if (len(bits) >= max_message.bit_length()+2):
            break
        bits += str(format(scaled[i] & ((1 << n_LSB) - 1), f'0{n_LSB}b'))

    # Parse metadata
    padding_bit = 4 # 2 bits for n_LSB, 1 bit for is_encrypt, 1 bit for is_random
    n_LSB = int(bits[0:2], 2) + 1
    is_encrypt = bits[2] == '1'
    is_random = bits[3] == '1'
    message_len = int(bits[padding_bit:max_message.bit_length()+padding_bit], 2)
    bits = '' if is_random else bits[max_message.bit_length()+padding_bit:]

    # Get message bits
    i = generate_rand_index(key, max_message.bit_length()+padding_bit, message_len, n_LSB, len(scaled)) if is_random else i
    while (i < len(scaled)) & (len(bits) <= message_len):
        bits += str(format(scaled[i] & ((1 << n_LSB) - 1), f'0{n_LSB}b'))
        i += 1
    bits = bits[:message_len]

    message_bytes = get_message_bytes(bits, is_encrypt, key)
    mime_type = get_mime_type(message_bytes)
    extension = get_extension_from_mime(mime_type)
    
    return {
        "data": message_bytes,
        "mime_type": mime_type,
        "extension": extension,
    }

def calculatePSNR(seg_original, seg_stego):
    originalAudio = np.array(AudioSegment.from_mp3(seg_original).get_array_of_samples())
    stegoAudio = np.array(AudioSegment.from_mp3(seg_stego).get_array_of_samples())
    mse = np.mean((originalAudio - stegoAudio) ** 2)
    if mse == 0:
        return float('inf')  # No noise, PSNR is infinite
    max_pixel = 2**15 - 1  # Max value for 16-bit audio
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return psnr

def generate_rand_index(key, lenbits_length, message_length, n_LSB, samples_length):
    seed = sum(ord(c) for c in key)
    random.seed(seed)

    frame_needed = message_length + (n_LSB - 1) // n_LSB
    lenbits_frame = (lenbits_length + (n_LSB - 1) // n_LSB)
    max_idx = samples_length - frame_needed
    return random.randint(lenbits_frame, max_idx)

# y = embed_message("tes.mp3", "Secret.txt", is_encrypt=False, key="BANA", is_random=True, n_LSB=8)
# print(y["psnr"])
# with open("output.mp3", "wb") as f:
#     f.write(y["data"])

# x = extract_message("output.mp3", key="BANA", n_LSB=8)
# print(x['extension'], x["mime_type"])
# with open("output"+x["extension"], "wb") as f:
#     f.write(x["data"])

# print(calculatePSNR("Sparkle.mp3", "output.mp3"))