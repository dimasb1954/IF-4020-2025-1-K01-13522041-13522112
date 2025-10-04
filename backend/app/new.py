from calendar import c
import re
from app.util import extract_frame_info, calc_bitrate, calc_sample_rate, calculate_frame_size
from app.util import get_mime_type, get_extension_from_mime
from app.util import read_file, write_file, get_file_size
from app.util import encrypt_vigenere, decrypt_vigenere
from app.util import generate_rand_index

def get_audio_frames(audio_data):
    frames = []
    i = 0
    while i < len(audio_data) - 4:
        if audio_data[i] == 0xFF and (audio_data[i+1] & 0xE0) == 0xE0:  # Sync bits
            try:
                frame_info = extract_frame_info(audio_data[i:i+4])
                bitrate = calc_bitrate(frame_info['version_id'], frame_info['layer_desc'], frame_info['bitrate_index'])
                sample_rate = calc_sample_rate(frame_info['version_id'], frame_info['sampling_rate_index'])
                if bitrate == 0 or sample_rate == 0:
                    i += 1
                    continue
                frame_size = calculate_frame_size(bitrate * 1000, sample_rate, frame_info['padding_bit'])
                frames.append((i, frame_size, frame_info['protection_bit'] == 0))
                i += frame_size
            except Exception as e:
                i += 1
        else:
            if len(frames) == 1:
                frames = []  # Reset if only one frame found and next is invalid
            i += 1
    return frames

### MESSAGE PROCESSING ###
def preprocess_message_metadata(filepath, max_message, is_encrypt=False, key="", is_random=False, n_LSB=1):
    with open(filepath, "rb") as f:
        content = f.read()
    
    if ( is_encrypt and key ):
        content = encrypt_vigenere(content.decode('latin1'), key).encode('latin1')
    bits = ''.join(format(byte, '08b') for byte in content)

    # Bits for file size info
    message_len = format(len(bits), '08b')
    len_bits = message_len.rjust(max_message.bit_length(), '0')
    print("Message Length (bits):", len_bits)

    return format(n_LSB-1, '02b')+str(is_encrypt&1)+str(is_random&1)+len_bits, bits

def get_message_bytes(bits, is_encrypt=False, key=""):
    message_bytes = bytearray()
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8:
            break
        message_bytes.append(int(byte, 2))

    if (is_encrypt and key):
        message_bytes = decrypt_vigenere(message_bytes.decode('latin1'), key).encode('latin1')

    return message_bytes

### MAIN FUNCTIONS ###
def embed_message(audio_path, message_path, is_encrypt=False, key="", is_random=False, n_LSB=1):
    with open(audio_path, 'rb') as f:
        audio_data = f.read()

    frames = get_audio_frames(audio_data)
    if not frames:
        raise ValueError("No valid MP3 frames found")

    stego_data = bytearray(audio_data)

    max_message = calc_max_message(frames, n_LSB)
    metadata_bits, message_bits = preprocess_message_metadata(message_path, max_message, is_encrypt, key, is_random, n_LSB)

    if ( 1 + (len(metadata_bits)-4 + (n_LSB-1))//n_LSB + (len(message_bits) + (n_LSB-1))//n_LSB > (max_message + (n_LSB-1))//n_LSB ):
        raise ValueError("Message size exceeds maximum capacity of the audio")

    padding_bit = 4 # 2 bits for n_LSB, 1 bit for is_encrypt, 1 bit for is_random

    bit_index = 0 # Index for message access

    frame_index = 0 # Current frame index
    n = padding_bit-1 # insert first byte using padding-bit's length LSB

    # Embed metadata bits in first bytes
    while frame_index < len(frames):
        frame_start, frame_size, has_crc = frames[frame_index]
        data_end = frame_start + frame_size
        current_bytes = frame_start + 4 + (2 if has_crc else 0)  # Current byte index in audio data

        while current_bytes < data_end:
            if metadata_bits[bit_index] == '0':
                stego_data[current_bytes] &= ~(1 << n)
            else:
                stego_data[current_bytes] |= (1 << n)
            
            bit_index += 1
            n -= 1

            if bit_index >= len(metadata_bits):
                current_bytes += 1
                break

            if n < 0:
                n = n_LSB-1
                current_bytes += 1
        
        if bit_index >= len(metadata_bits):
            if (current_bytes >= data_end):
                frame_index += 1
                current_bytes = -1 # Start from next frame
            last_metadata_frame = frame_index
            last_metadata_bytes = current_bytes
            break
        
        frame_index += 1
    else:
        raise ValueError("Not enough space to embed metadata")
    
    # Embed message bits in subsequent frames
    bit_index = 0 # Reset bit index for message
    rand_index = generate_rand_index(key, last_metadata_frame, len(frames)) if is_random else 0 # Random start frame index [0, len_avail_frames]
    n = n_LSB - 1

    frame_index = 0 # For counting embedded frames for content
    len_avail_frames = len(frames) - last_metadata_frame
    while frame_index < len_avail_frames:
        curr_frame_index = ((frame_index + rand_index) % len_avail_frames) + last_metadata_frame
        frame_start, frame_size, has_crc = frames[curr_frame_index]
        data_end = frame_start + frame_size
        current_bytes = last_metadata_bytes if (last_metadata_bytes != -1 and last_metadata_frame == curr_frame_index) else frame_start + 4 + (2 if has_crc else 0)

        while current_bytes < data_end:
            if message_bits[bit_index] == '0':
                stego_data[current_bytes] &= ~(1 << n)
            else:
                stego_data[current_bytes] |= (1 << n)

            bit_index += 1
            n -= 1

            if n < 0:
                n = n_LSB - 1
                current_bytes += 1

            if bit_index >= len(message_bits):
                break

        frame_index += 1
        if bit_index >= len(message_bits):
            break
    else:
        raise ValueError("Not enough space to embed content")

    return bytes(stego_data)

def extract_message(stego_path, key=""):
    with open(stego_path, 'rb') as f:
        audio_data = f.read()

    frames = get_audio_frames(audio_data)
    if not frames:
        raise ValueError("No valid MP3 frames found")
    
    stego_data = bytearray(audio_data)
    
    padding_bit = 4 # 2 bits for n_LSB, 1 bit for is_encrypt, 1 bit for is_random
    frame_index = 0

    # Get Flag & LSB Info
    frame_start, frame_size, has_crc = frames[frame_index]
    current_bytes = frame_start + 4 + (2 if has_crc else 0)
    flag_bits = format(stego_data[current_bytes] & ((1 << (padding_bit)) - 1), '04b')
    current_bytes += 1

    n_LSB = int(flag_bits[:2], 2) + 1
    is_encrypt = flag_bits[2] == '1'
    is_random = flag_bits[3] == '1'

    print(f"n_LSB: {n_LSB}, is_encrypt: {is_encrypt}, is_random: {is_random}")

    # Get message length info
    message_length_bits = ''
    max_message = calc_max_message(frames, n_LSB)
    expect_len_bits = max_message.bit_length()

    while frame_index < len(frames):
        frame_start, frame_size, has_crc = frames[frame_index]
        data_end = frame_start + frame_size
        current_bytes = frame_start + 4 + (2 if has_crc else 0)

        while current_bytes < data_end:
            message_length_bits += format(stego_data[current_bytes] & ((1 << n_LSB) - 1), f'0{n_LSB}b')

            current_bytes += 1
            if len(message_length_bits)-n_LSB >= expect_len_bits:
                break

        if len(message_length_bits)-n_LSB >= expect_len_bits:
            if (current_bytes >= data_end):
                frame_index += 1
                current_bytes = -1 # Start from next frame
            last_metadata_frame = frame_index
            last_metadata_bytes = current_bytes
            break
        frame_index += 1

    if len(message_length_bits)-n_LSB < expect_len_bits:
        raise ValueError("Not enough data to extract message length")
    
    message_length = int(message_length_bits[n_LSB:expect_len_bits+n_LSB], 2)
    print("Message Length (bits):", message_length)

    # Get message bits
    message_bits = ''
    rand_index = generate_rand_index(key, last_metadata_frame, len(frames)) if is_random else 0 # Random start frame index [0, len_avail_frames]
    n = n_LSB - 1

    frame_index = 0 # For counting embedded frames for content
    len_avail_frames = len(frames) - last_metadata_frame + 1
    while frame_index < len_avail_frames:
        curr_frame_index = ((frame_index + rand_index) % len_avail_frames) + last_metadata_frame
        frame_start, frame_size, has_crc = frames[curr_frame_index]
        data_end = frame_start + frame_size
        current_bytes = last_metadata_bytes if (last_metadata_bytes != -1 and last_metadata_frame == curr_frame_index) else frame_start + 4 + (2 if has_crc else 0)

        while current_bytes < data_end:
            message_bits += format(stego_data[current_bytes] & ((1 << n_LSB) - 1), f'0{n_LSB}b')

            if len(message_bits) >= message_length:
                break
            current_bytes += 1
        
        if len(message_bits) >= message_length:
            break
        frame_index += 1
        
    if len(message_bits) < message_length:
        raise ValueError("Not enough data to extract message content")
    
    message_bytes = get_message_bytes(message_bits[:message_length], is_encrypt, key)
    mime_type = get_mime_type(message_bytes)
    extension = get_extension_from_mime(mime_type)

    print("Extracted Message:", message_bytes)
    print("MIME Type:", mime_type)
    print("File Extension:", extension)

    return {
        "data": message_bytes,
        "mime_type": mime_type,
        "extension": extension
    }

def calc_max_message(frames, n_LSB=1):
    total_bytes = 0
    for frame_start, frame_size, has_crc in frames:
        data_start = frame_start + 4 + (2 if has_crc else 0)
        data_end = frame_start + frame_size
        total_bytes += (data_end - data_start)
    return total_bytes * n_LSB

# def main():
#     stego_data = embed_message('test_song.mp3', 'test.txt', is_encrypt=True, key='BANAMAN', is_random=True, n_LSB=2)

#     with open('stego.mp3', 'wb') as f:
#         f.write(stego_data)

#     extracted_message = extract_message('stego.mp3', key='BANAMAN')
#     # message = "HELLO WORLD!!! YIPPIIEEEE"
#     print("Extracted Message:", extracted_message)
#     with open('extracted_message' + extracted_message['extension'], 'wb') as f:
#         f.write(extracted_message['data'])

#     # print("Extracted Message:", extracted_message)
    
# main()
# extract_frame_info(b'\xff\xfb\xe0\x64d')