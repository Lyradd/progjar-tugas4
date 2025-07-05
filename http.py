import sys
import os
import socket
import logging
import base64
from urllib.parse import parse_qs, unquote

# Direktori untuk menyimpan file yang diunggah dan disajikan
UPLOAD_DIR = "files"

class Http:
    def __init__(self):
        """
        Konstruktor kelas Http.
        """
        pass

    def send_response(self, code, body, content_type='text/plain; charset=utf-8'):
        """
        Membangun dan mengirim respons HTTP standar.
        Args:
            code (int): Kode status HTTP (misal: 200, 404).
            body (bytes): Konten dari body respons.
            content_type (str): Tipe konten (misal: 'text/html').
        """
        status_line = f"HTTP/1.1 {code}\r\n"
        headers = f"Content-Type: {content_type}\r\n"
        headers += f"Content-Length: {len(body)}\r\n"
        headers += "Connection: close\r\n\r\n"
        response = status_line.encode('utf-8') + headers.encode('utf-8') + body
        try:
            self.connection.sendall(response)
        except Exception as e:
            logging.error(f"Error sending response: {e}")

    def get_request(self):
        """
        Membaca dan mem-parsing request HTTP dari koneksi yang masuk.
        Membaca header hingga `\r\n\r\n`, kemudian membaca body berdasarkan `Content-Length`.
        Returns:
            dict or None: Dictionary berisi detail request atau None jika request tidak valid.
        """
        raw_request = b""
        # Terus baca dari socket sampai menemukan akhir dari header
        while b"\r\n\r\n" not in raw_request:
            chunk = self.connection.recv(2048)
            if not chunk:
                break
            raw_request += chunk
        
        if not raw_request:
            return None

        header_part, body_part = raw_request.split(b"\r\n\r\n", 1)
        headers_list = header_part.decode('utf-8', errors='ignore').split("\r\n")
        
        request_line = headers_list[0]
        try:
            method, uri, version = request_line.split()
        except ValueError:
            return None

        headers = {}
        for line in headers_list[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                headers[key.lower()] = value

        # Baca sisa body jika `Content-Length` lebih besar dari body yang sudah terbaca
        content_length = int(headers.get('content-length', 0))
        while len(body_part) < content_length:
            more = self.connection.recv(min(2048, content_length - len(body_part)))
            if not more:
                break
            body_part += more
            
        return {
            'method': method,
            'uri': uri,
            'version': version,
            'headers': headers,
            'body': body_part
        }

    def process(self, connection, address):
        """
        Titik masuk utama untuk memproses satu koneksi klien.
        """
        self.connection = connection
        self.address = address
        
        request = self.get_request()
        if not request:
            self.connection.close()
            return

        method = request['method']
        uri = request['uri']
        
        # --- ROUTING LOGIC ---
        if method == 'GET' and uri == '/list':
            self.handle_list()
        elif method == 'POST' and uri == '/upload':
            self.handle_upload(request)
        elif method == 'GET' and uri.startswith('/delete/'):
            self.handle_delete(uri)
        elif method == 'GET':
            # Ini menangani permintaan untuk file spesifik dan root path
            self.handle_get(uri)
        else:
            self.send_response(405, b'Method Not Allowed')
        
        self.connection.close()
        logging.info(f"Connection from {address} closed.")

    def handle_list(self):
        """Handler untuk GET /list. Menampilkan daftar file."""
        try:
            files = os.listdir(UPLOAD_DIR)
            if not files:
                body = "<h1>Directory is empty.</h1>"
            else:
                # Membuat daftar file sebagai link HTML
                list_items = "".join([f"<li><a href='/{f}'>{f}</a></li>" for f in files])
                body = f"<h1>Files in '{UPLOAD_DIR}':</h1><ul>{list_items}</ul>"
            self.send_response(200, body.encode('utf-8'), 'text/html; charset=utf-8')
        except Exception as e:
            logging.error(f"Error listing files: {e}")
            self.send_response(500, f"Internal Server Error: {e}".encode())

    def handle_upload(self, request):
        """Handler untuk POST /upload. Menyimpan file yang diunggah."""
        try:
            body = request['body'].decode('utf-8')
            parsed_body = parse_qs(body)
            
            filename = parsed_body.get('filename', [None])[0]
            filedata_b64 = parsed_body.get('data', [None])[0]

            if not filename or not filedata_b64:
                self.send_response(400, b'Bad Request: Missing filename or data')
                return

            # Membersihkan nama file dan decode dari base64
            filename = os.path.basename(unquote(filename))
            filepath = os.path.join(UPLOAD_DIR, filename)
            filedata = base64.b64decode(filedata_b64)

            with open(filepath, 'wb') as f:
                f.write(filedata)
            
            logging.info(f"File '{filename}' uploaded successfully from {self.address}.")
            self.send_response(200, f"File '{filename}' uploaded successfully.".encode())
        except Exception as e:
            logging.error(f"Error uploading file: {e}")
            self.send_response(500, f"Internal Server Error: {e}".encode())

    def handle_delete(self, uri):
        """Handler untuk GET /delete/{filename}. Menghapus file."""
        try:
            filename = os.path.basename(unquote(uri.split('/')[-1]))
            if not filename:
                self.send_response(400, b'Bad Request: Filename not specified')
                return

            filepath = os.path.join(UPLOAD_DIR, filename)

            if os.path.isfile(filepath):
                os.remove(filepath)
                logging.info(f"File '{filename}' deleted by {self.address}.")
                self.send_response(200, f"File '{filename}' deleted.".encode())
            else:
                self.send_response(404, f"File '{filename}' not found.".encode())
        except Exception as e:
            logging.error(f"Error deleting file: {e}")
            self.send_response(500, f"Internal Server Error: {e}".encode())

    def handle_get(self, uri):
        """Handler untuk GET /{filename}. Menyajikan file statis."""
        filename = os.path.basename(unquote(uri.strip('/')))
        
        # Jika path root, tampilkan daftar file sebagai halaman utama
        if not filename:
            self.handle_list()
            return
            
        filepath = os.path.join(UPLOAD_DIR, filename)

        if os.path.isfile(filepath):
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                
                # Menentukan Content-Type secara sederhana
                content_type = 'application/octet-stream'
                if filename.endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif filename.endswith('.png'):
                    content_type = 'image/png'
                elif filename.endswith('.txt'):
                    content_type = 'text/plain'
                elif filename.endswith('.html'):
                    content_type = 'text/html'
                
                self.send_response(200, content, content_type)
            except Exception as e:
                logging.error(f"Error reading file {filename}: {e}")
                self.send_response(500, f"Internal Server Error: {e}".encode())
        else:
            self.send_response(404, f"File '{filename}' not found.".encode())
