import sys
import socket
import json
import logging
import ssl
import os
import base64

# Alamat server, ganti 'localhost' jika server berjalan di mesin lain
server_address = ('localhost', 8889)
# File yang akan diunggah
FILE_TO_UPLOAD = 'client_image.jpg'
# File yang akan dihapus (sama dengan yang diunggah)
FILE_TO_DELETE = 'client_image.jpg'


def make_socket(destination_address='localhost', port=8889):
    """Membuat socket TCP standar."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10) # Timeout 10 detik
        sock.connect((destination_address, port))
        return sock
    except Exception as ee:
        logging.error(f"Error creating socket: {str(ee)}")
        return None


def make_secure_socket(destination_address='localhost', port=8889):
    """Membuat socket TCP yang aman (SSL/TLS)."""
    try:
        # Konteks SSL default, tanpa verifikasi sertifikat (hanya untuk development)
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((destination_address, port))
        secure_socket = context.wrap_socket(sock, server_hostname=destination_address)
        logging.info(f"SSL established with {secure_socket.version()}")
        return secure_socket
    except Exception as ee:
        logging.error(f"Error creating secure socket: {str(ee)}")
        return None


def send_request(request_str, is_secure=False):
    """Mengirim request HTTP ke server dan menerima respons."""
    alamat_server, port_server = server_address
    
    # Pilih socket biasa atau aman
    if is_secure:
        sock = make_secure_socket(alamat_server, port_server)
    else:
        sock = make_socket(alamat_server, port_server)

    if sock is None:
        return ""

    logging.warning(f"Sending request:\n------\n{request_str.strip()}\n------")
    try:
        sock.sendall(request_str.encode('utf-8'))

        # Menerima respons secara bertahap
        response_bytes = b""
        while True:
            chunk = sock.recv(2048)
            if not chunk:
                break
            response_bytes += chunk
        
        return response_bytes.decode('utf-8', errors='ignore')

    except Exception as ee:
        logging.error(f"Error during data exchange: {str(ee)}")
        return ''
    finally:
        sock.close()


def build_upload_request(filepath):
    """Membangun request HTTP POST untuk mengunggah file."""
    if not os.path.isfile(filepath):
        logging.error(f"File '{filepath}' not found for upload.")
        return None
    
    with open(filepath, 'rb') as f:
        filedata = f.read()
    
    filename = os.path.basename(filepath)
    # Encode data file ke base64
    filedata_b64 = base64.b64encode(filedata).decode()
    
    # Body dalam format x-www-form-urlencoded
    body = f'filename={filename}&data={filedata_b64}'
    body_bytes = body.encode('utf-8')
    content_length = len(body_bytes)

    # Request POST
    request = (
        f'POST /upload HTTP/1.1\r\n'
        f'Host: {server_address[0]}\r\n'
        f'Content-Length: {content_length}\r\n'
        f'Content-Type: application/x-www-form-urlencoded\r\n'
        f'Connection: close\r\n'
        f'\r\n'
        f'{body}'
    )
    return request


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # 1. LIST: Meminta daftar file di server (seharusnya kosong di awal)
    print("\n--- 1. LIST DIRECTORY (AWAL) ---")
    list_request = f'GET /list HTTP/1.1\r\nHost: {server_address[0]}\r\nConnection: close\r\n\r\n'
    print(send_request(list_request))

    # 2. UPLOAD: Mengunggah file
    print(f"\n--- 2. UPLOAD FILE '{FILE_TO_UPLOAD}' ---")
    upload_request = build_upload_request(FILE_TO_UPLOAD)
    if upload_request:
        print(send_request(upload_request))
    else:
        print(f"Upload failed because file '{FILE_TO_UPLOAD}' was not found.")

    # 3. LIST: Memeriksa daftar file setelah upload
    print("\n--- 3. LIST SETELAH UPLOAD ---")
    print(send_request(list_request))

    # 4. GET (FAIL): Mencoba melihat file yang tidak ada
    print("\n--- 4. LIHAT FILE (Contoh Gagal) ---")
    get_fail_req = f'GET /non_existent_file.txt HTTP/1.1\r\nHost: {server_address[0]}\r\nConnection: close\r\n\r\n'
    print(send_request(get_fail_req))

    # 5. DELETE: Menghapus file yang tadi diunggah
    print(f"\n--- 5. DELETE '{FILE_TO_DELETE}' ---")
    delete_request = f'GET /delete/{FILE_TO_DELETE} HTTP/1.1\r\nHost: {server_address[0]}\r\nConnection: close\r\n\r\n'
    print(send_request(delete_request))

    # 6. LIST: Memeriksa daftar file setelah delete
    print("\n--- 6. LIST SETELAH DELETE ---")
    print(send_request(list_request))
