### MIME TYPE UTILITIES ###
import magic
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

### FILE UTILITIES ###
import os
def get_file_size(file_path):
    return os.path.getsize(file_path)

def read_file(file_path):
    with open(file_path, "rb") as f:
        return f.read()

def write_file(file_path, data):
    with open(file_path, "wb") as f:
        f.write(data)

### RANDOM UTILITIES ###
import random
def generate_rand_index(key, last_metadata_frame, frame_count): # Range: [0, len_avail_frames])
    seed = sum(ord(c) for c in key)
    random.seed(seed)

    return random.randint(0, frame_count - last_metadata_frame + 1)

### CRYPTOGRAPHY UTILITIES ###
def encrypt_vigenere(plaintext, key):
    if (key == ""):
        return plaintext
    ciphertext = []
    if len(key) < len(plaintext):
        key = key + plaintext[:len(plaintext)-len(key)]

    for i, char in enumerate(plaintext):
        p = ord(char)
        k = ord(key[i])
        c = (p + k) % 256
        ciphertext.append(chr(c))
    return ''.join(ciphertext)

def decrypt_vigenere(ciphertext, key):
    if (key == ""):
        return ciphertext
    plaintext = []
    for i, char in enumerate(ciphertext):
        c = ord(char)
        k = ord(key[i])
        p = (c - k) % 256
        plaintext.append(chr(p))
        key += chr(p)
    return ''.join(plaintext)

### FRAME HEADER UTILITIES ###
def calculate_frame_size(bitrate, sample_rate, padding=0):
    return (144 * bitrate // sample_rate) + padding

def calc_bitrate(version_id, layer_desc, bitrate_index):
    BITRATE_TABLE = {
        (3, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320], # MPEG1 Layer I
        (3, 2): [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384], # MPEG1 Layer II
        (3, 1): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320], # MPEG1 Layer III
        (2, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224], # MPEG2 Layer I
        (2, 2): [0, 8 ,16 ,24 ,32 ,40 ,48 ,56 ,64 ,80 ,96 ,112 ,128 ,144 ,160], # MPEG2 Layer II
        (2, 1): [0, 8 ,16 ,24 ,32 ,40 ,48 ,56 ,64 ,80 ,96 ,112 ,128 ,144 ,160], # MPEG2 Layer III
        (0, 3): [0,32 ,40 ,48 ,56 ,64 ,80 ,96 ,112 ,128 ,144 ,160 ,176 ,192 ,224], # MPEG2.5 Layer I
        (0, 2): [0,8 ,16 ,24 ,32 ,40 ,48 ,56 ,64 ,80 ,96 ,112 ,128 ,144 ,160], # MPEG2.5 Layer II
        (0, 1): [0,8 ,16 ,24 ,32 ,40 ,48 ,56 ,64 ,80 ,96 ,112 ,128 ,144 ,160], # MPEG2.5 Layer III
    }
    return BITRATE_TABLE.get((version_id, layer_desc), [0]*15)[bitrate_index]

def calc_sample_rate(version_id, sampling_rate_index):
    SAMPLE_RATE_TABLE = {
        0: [11025, 12000, 8000],  # MPEG 2.5
        2: [22050, 24000, 16000], # MPEG 2
        3: [44100, 48000, 32000], # MPEG 1
    }
    return SAMPLE_RATE_TABLE.get(version_id, [0]*3)[sampling_rate_index]

def extract_frame_info(frame_header):
    if len(frame_header) < 4:
        raise ValueError("Frame header must be at least 4 bytes long")

    header = int.from_bytes(frame_header[:4], byteorder='big')

    # Extract fields using bitwise operations
    sync = (header >> 21) & 0x7FF
    version_id = (header >> 19) & 0x3
    layer_desc = (header >> 17) & 0x3
    protection_bit = (header >> 16) & 0x1
    bitrate_index = (header >> 12) & 0xF
    sampling_rate_index = (header >> 10) & 0x3
    padding_bit = (header >> 9) & 0x1
    private_bit = (header >> 8) & 0x1
    channel_mode = (header >> 6) & 0x3
    mode_extension = (header >> 4) & 0x3

    return {
        'sync': sync,
        'version_id': version_id,
        'layer_desc': layer_desc,
        'protection_bit': protection_bit,
        'bitrate_index': bitrate_index,
        'sampling_rate_index': sampling_rate_index,
        'padding_bit': padding_bit,
        'private_bit': private_bit,
        'channel_mode': channel_mode,
        'mode_extension': mode_extension
    }