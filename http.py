import sys
import os
import socket
import logging
import base64
from urllib.parse import parse_qs, unquote, urlencode


class Http:
    def __init__(self):
        pass

    def send_response(self, code, body, content_type='text/plain; charset=utf-8'):
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
        raw_request = b""
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
        self.connection = connection
        self.address = address
        
        request = self.get_request()
        if not request:
            self.connection.close()
            return

        method = request['method']
        uri = request['uri']
        
        if method == 'GET' and (uri == '/list' or uri == '/'):
            self.handle_list()
        elif method == 'POST' and uri == '/upload':
            self.handle_upload(request)
        elif method == 'GET' and uri.startswith('/delete/'):
            self.handle_delete(uri)
        elif method == 'GET':
            self.handle_get(uri)
        else:
            self.send_response(405, b'Method Not Allowed')
        
        self.connection.close()

    def handle_list(self):
        try:
            files = os.listdir('.')
            if not files:
                body = "Current directory is empty."
            else:
                body = "\n".join(files)
            self.send_response(200, body.encode('utf-8'), 'text/plain; charset=utf-8')
        except Exception as e:
            logging.error(f"Error listing files: {e}")
            self.send_response(500, f"Internal Server Error: {e}".encode())

    def handle_upload(self, request):
        try:
            body = request['body'].decode('utf-8')
            parsed_body = parse_qs(body)
            
            filename = parsed_body.get('filename', [None])[0]
            filedata_b64 = parsed_body.get('data', [None])[0]

            if not filename or not filedata_b64:
                self.send_response(400, b'Bad Request: Missing filename or data')
                return

            filename = os.path.basename(unquote(filename))
            # --- PERUBAHAN DI SINI ---
            # Menyimpan file di direktori saat ini, bukan di UPLOAD_DIR
            filepath = filename
            filedata = base64.b64decode(filedata_b64)

            with open(filepath, 'wb') as f:
                f.write(filedata)
            
            logging.info(f"File '{filename}' uploaded successfully.")
            self.send_response(200, f"File '{filename}' uploaded successfully.".encode())
        except Exception as e:
            logging.error(f"Error uploading file: {e}")
            self.send_response(500, f"Internal Server Error: {e}".encode())

    def handle_delete(self, uri):
        try:
            filename = os.path.basename(unquote(uri.split('/')[-1]))
            if not filename:
                self.send_response(400, b'Bad Request: Filename not specified')
                return

            # --- PERUBAHAN DI SINI ---
            # Menghapus file dari direktori saat ini, bukan dari UPLOAD_DIR
            filepath = filename

            if os.path.isfile(filepath):
                os.remove(filepath)
                logging.info(f"File '{filename}' deleted.")
                self.send_response(200, f"File '{filename}' deleted.".encode())
            else:
                self.send_response(404, f"File '{filename}' not found.".encode())
        except Exception as e:
            logging.error(f"Error deleting file: {e}")
            self.send_response(500, f"Internal Server Error: {e}".encode())

    def handle_get(self, uri):
        filename = os.path.basename(unquote(uri.strip('/')))
        
        # --- PERUBAHAN DI SINI ---
        # Mengambil file dari direktori saat ini, bukan dari UPLOAD_DIR
        filepath = filename

        if os.path.isfile(filepath):
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                
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