from email import mime
from turtle import st
from pydub import AudioSegment
import magic
import numpy as np
import binascii

def parse_frame_length(header_bytes):
    # header_bytes = 4 bytes
    b1, b2, b3, b4 = header_bytes
    bitrate_index = (b3 >> 4) & 0x0F
    samplerate_index = (b3 >> 2) & 0x03
    padding = (b3 >> 1) & 0x01

    # tabel bitrate MPEG1 Layer III (kbps)
    bitrate_table = {
        0x01: 32, 0x02: 40, 0x03: 48, 0x04: 56,
        0x05: 64, 0x06: 80, 0x07: 96, 0x08: 112,
        0x09: 128, 0x0A: 160, 0x0B: 192, 0x0C: 224,
        0x0D: 256, 0x0E: 320
    }
    # tabel sample rate MPEG1
    samplerate_table = {0: 44100, 1: 48000, 2: 32000}

    bitrate = bitrate_table.get(bitrate_index, None)
    samplerate = samplerate_table.get(samplerate_index, None)

    if bitrate is None or samplerate is None:
        return None

    # rumus panjang frame (MPEG1 Layer III)
    frame_length = int((144000 * bitrate * 1000 // samplerate) + padding)
    return frame_length


def extract_frames(mp3_path, n=5):
    with open(mp3_path, "rb") as f:
        data = f.read()

    frames = []
    i = 0
    while i < len(data) - 4 and len(frames) < n:
        if data[i] == 0xFF and (data[i+1] & 0xE0) == 0xE0:
            header = data[i:i+4]
            frame_len = parse_frame_length(header)
            if frame_len is None:
                i += 1
                continue
            frame = data[i:i+frame_len]
            frames.append(frame.hex(" "))
            i += frame_len
        else:
            i += 1
    return frames

def get_mime_type(bytes_data):
    return magic.from_buffer(bytes_data, mime=True)

def get_extension_from_mime(mime_type):
    MIME_TO_EXT = {
        'audio/mpeg': '.mp3',
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'application/pdf': '.pdf',
        'application/zip': '.zip',
        'application/msword': '.doc',
        'text/plain': '.txt',
        'text/html': '.html',
        'application/json': '.json',
        'application/xml': '.xml',
        'video/mp4': '.mp4'
    }
    return MIME_TO_EXT.get(mime_type, '.bin') 

# Preprocess message file to bits with metadata
def preprocess_message_metadata(filepath, mp3_size, is_encrypt=False, key=""):
    with open(filepath, "rb") as f:
        content = f.read()

    if is_encrypt and key:
        content = encrypt_vigenere(content.decode('latin1'), key).encode('latin1')
    bits = ''.join(format(byte, '08b') for byte in content)

    # Bits for file size info
    message_len = format(len(bits), '08b')
    len_bits = message_len.ljust(mp3_size.bit_length(), '0')

    return len_bits + bits

def get_message_bytes(bits, mp3_size, is_encrypt=False, key=""):
    len_bits = bits[:mp3_size.bit_length()]
    message_len = int(len_bits, 2)

    message_bits = bits[mp3_size.bit_length():mp3_size.bit_length() + message_len]
    message_bytes = bytearray()
    for i in range(0, message_len, 8):
        byte = message_bits[i:i+8]
        if len(byte) < 8:
            break
        message_bytes.append(int(byte, 2))
    

    if is_encrypt and key:
        message_bytes = decrypt_vigenere(message_bytes.decode('latin1'), key).encode('latin1')

    return message_bytes

# Auto key Vigenere cipher
# Plaintext is bytes and returns ciphertext bytes
def encrypt_vigenere(plaintext, key):
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
    plaintext = []

    for i, char in enumerate(ciphertext):
        c = ord(char)
        k = ord(key[i])
        p = (c - k) % 256
        plaintext.append(chr(p))
        key += chr(p)  # Auto key extension
    return ''.join(plaintext)

def embed_message(audio_path, message_path, is_encrypt=False, key=""):
    # Load audio
    audio = AudioSegment.from_mp3(audio_path)
    raw = audio.raw_data
    channels = audio.channels
    sample_width = audio.sample_width
    frame_rate = audio.frame_rate
    mp3_size = len(raw)

    if sample_width != 2:
        raise ValueError("Only 16-bit PCM is supported")
    
    samples = np.frombuffer(raw, dtype=np.int16)
    norm = samples.astype(np.float32) / (2**15) 
    scaled = (norm * 1e6).astype(int)

    message_bits = preprocess_message_metadata(message_path, mp3_size, is_encrypt, key)
    stego_scaled = scaled.copy()

    for i, bit in enumerate(message_bits):
        if bit == '0':
            stego_scaled[i] = (stego_scaled[i] & ~1)
        else:
            stego_scaled[i] = (stego_scaled[i] | 1)

    stego_norm = stego_scaled.astype(np.float32) / 1e6
    stego_pcm = (stego_norm * (2**15)).astype(np.int16)

    stego_audio = AudioSegment(
        data=stego_pcm.tobytes(),
        sample_width=2,
        frame_rate=frame_rate,
        channels=channels
    )

    stego_bytes = stego_audio.export(format="mp3").read()
    return stego_bytes

def extract_message(stego_path, is_decrypt=False, key=""):
    audio = AudioSegment.from_mp3(stego_path)
    raw = audio.raw_data
    sample_width = audio.sample_width

    if sample_width != 2:
        raise ValueError("Only 16-bit PCM is supported")

    samples = np.frombuffer(raw, dtype=np.int16)
    norm = samples.astype(np.float32) / (2**15)
    scaled = (norm * 1e6).astype(int)

    bits = ''.join('1' if (sample & 1) else '0' for sample in scaled)

    message_bytes = get_message_bytes(bits, len(raw), is_decrypt, key)
    mime_type = get_mime_type(message_bytes)
    extension = get_extension_from_mime(mime_type)
    
    return message_bytes, mime_type, extension 

# # ====== 1. Load MP3 & decode ======
# audio = AudioSegment.from_mp3("tes.mp3")
# raw = audio.raw_data
# channels = audio.channels
# sample_width = audio.sample_width
# frame_rate = audio.frame_rate

# # frames = extract_frames("input.mp3", n=5)
# # for idx, frame in enumerate(frames):
# #     print(f"\n=== Frame {idx} (len={len(bytes.fromhex(frame))}) ===")
# #     print(frame[:100] + " ...")  # tampilkan 100 karakter pertama saja biar ringkas

# if sample_width == 2:
#     samples = np.frombuffer(raw, dtype=np.int16)
# else:
#     raise ValueError("Hanya support 16-bit PCM")

# # ====== 2. Normalisasi & scaling ======
# norm = samples.astype(np.float32) / (2**15)
# scaled = (norm * 1e6).astype(int)

# # ====== 3. Pesan ======
# message = "KRIPTOGRAFI"
# message_bits = ''.join(format(ord(c), '08b') for c in message)

# print("Pesan:", message)
# print("Pesan biner:", message_bits)

# # ====== 4. Simpan salinan sebelum embedding ======
# scaled_before = scaled.copy()

# # ====== 5. Embedding ======
# stego_scaled = scaled.copy()
# for i, bit in enumerate(message_bits):
#     if bit == '0':
#         stego_scaled[i] = (stego_scaled[i] & ~1)
#     else:
#         stego_scaled[i] = (stego_scaled[i] | 1)

# # ====== 6. Denormalisasi ======
# stego_norm = stego_scaled.astype(np.float32) / 1e6
# stego_pcm = (stego_norm * (2**15)).astype(np.int16)

# # ====== 7. Tampilkan hex sebelum & sesudah (hanya sampel awal) ======
# print("\nPerbandingan hex (sampel awal):")
# for i in range(16):  # tampilkan 16 sampel pertama
#     before_hex = (int(scaled_before[i])).to_bytes(4, "big", signed=True).hex()
#     after_hex  = (int(stego_scaled[i])).to_bytes(4, "big", signed=True).hex()
#     print(f"Sampel {i:03d}: before={before_hex}  after={after_hex}")

# # ====== 8. Simpan hasil stego ======
# stego_audio = AudioSegment(
#     data=stego_pcm.tobytes(),
#     sample_width=2,
#     frame_rate=frame_rate,
#     channels=channels
# )
# stego_audio.export("stego_output.mp3", format="mp3")

# print("\nStego audio berhasil disimpan sebagai stego_output.mp3")
