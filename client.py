import sys
import socket
import logging
import os
import base64
# Import yang diperlukan ditambahkan
from urllib.parse import urlencode

# Alamat server sudah diarahkan ke 172.16.16.101
server_address = ('172.16.16.101', 8889)
FILE_TO_UPLOAD = 'client_image.jpg'
FILE_TO_DELETE = 'client_delete.jpg'


def make_socket(destination_address='localhost', port=8889):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((destination_address, port))
        return sock
    except Exception as ee:
        logging.error(f"Error creating socket: {str(ee)}")
        return None


def send_request(request_str):
    alamat_server, port_server = server_address
    sock = make_socket(alamat_server, port_server)

    if sock is None:
        return ""

    logging.warning(f"Sending request:\n------\n{request_str.strip()}\n------")
    try:
        sock.sendall(request_str.encode('utf-8'))
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
    filedata_b64 = base64.b64encode(filedata).decode()
    
    # -- PERUBAHAN DI SINI --
    # Menggunakan urlencode untuk membuat body yang aman
    payload = {'filename': filename, 'data': filedata_b64}
    body = urlencode(payload)
    # -----------------------

    body_bytes = body.encode('utf-8')
    content_length = len(body_bytes)

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

    # 1. LIST: Meminta daftar file di server
    print("\n--- 1. LIST DIRECTORY (AWAL) ---")
    list_request = f'GET /list HTTP/1.1\r\nHost: {server_address[0]}\r\nConnection: close\r\n\r\n'
    print(send_request(list_request))

    # 2. UPLOAD: Mengunggah file
    print(f"\n--- 2. UPLOAD FILE '{FILE_TO_UPLOAD}' ---")
    if not os.path.exists(FILE_TO_UPLOAD):
        with open(FILE_TO_UPLOAD, "w") as f:
            f.write("This is a dummy file for testing.")
        print(f"'{FILE_TO_UPLOAD}' not found, created a dummy file.")

    upload_request = build_upload_request(FILE_TO_UPLOAD)
    if upload_request:
        print(send_request(upload_request))

    # 3. LIST: Memeriksa daftar file setelah upload
    print("\n--- 3. LIST SETELAH UPLOAD ---")
    list_request_after = f'GET /list HTTP/1.1\r\nHost: {server_address[0]}\r\nConnection: close\r\n\r\n'
    print(send_request(list_request_after))

    # 4. GET (FAIL): Mencoba melihat file yang tidak ada
    print("\n--- 4. LIHAT FILE (Contoh Gagal) ---")
    get_fail_req = f'GET /client_image.jpg HTTP/1.1\r\nHost: {server_address[0]}\r\nConnection: close\r\n\r\n'
    print(send_request(get_fail_req))

    # 5. DELETE: Menghapus file yang tadi diunggah
    print(f"\n--- 5. DELETE '{FILE_TO_DELETE}' ---")
    delete_request = f'GET /delete/{FILE_TO_DELETE} HTTP/1.1\r\nHost: {server_address[0]}\r\nConnection: close\r\n\r\n'
    print(send_request(delete_request))

    # 6. LIST: Memeriksa daftar file setelah delete
    print("\n--- 6. LIST SETELAH DELETE ---")
    list_request_final = f'GET /list HTTP/1.1\r\nHost: {server_address[0]}\r\nConnection: close\r\n\r\n'
    print(send_request(list_request_final))