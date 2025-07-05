from socket import *
import socket
import threading
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from http import Http

# Direktori untuk file, harus sama dengan yang di http.py
UPLOAD_DIR = "files"

class ClientHandlerThread(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__()
        self.conn = conn
        self.addr = addr
        # Setiap thread memiliki instance Http-nya sendiri
        self.http_handler = Http()

    def run(self):
        try:
            self.http_handler.process(self.conn, self.addr)
        except Exception as e:
            logging.error(f"Error in thread for {self.addr}: {e}")
        finally:
            self.conn.close()


class Server:
    def __init__(self, portnumber):
        self.portnumber = portnumber
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Menggunakan ThreadPoolExecutor untuk mengelola thread
        self.executor = ThreadPoolExecutor(max_workers=10)

    def start(self):
        # Memastikan direktori upload ada sebelum server mulai
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)
            logging.info(f"Created directory: {UPLOAD_DIR}")

        self.my_socket.bind(('0.0.0.0', self.portnumber))
        self.my_socket.listen(5)
        logging.warning(f"Server (Thread Pool) listening on port {self.portnumber}")

        while True:
            try:
                conn, addr = self.my_socket.accept()
                logging.warning(f"Connection from {addr}")
                
                # Menyerahkan penanganan koneksi ke thread pool
                self.executor.submit(self.handle_client, conn, addr)
                
            except KeyboardInterrupt:
                logging.warning("Server shutting down.")
                break
            except Exception as e:
                logging.error(f"Error accepting connections: {e}")
        
        self.shutdown()

    def handle_client(self, conn, addr):
        """Fungsi yang akan dijalankan oleh setiap thread di pool."""
        try:
            http_handler = Http()
            http_handler.process(conn, addr)
        except Exception as e:
            logging.error(f"Error handling client {addr}: {e}")
        finally:
            conn.close()

    def shutdown(self):
        self.executor.shutdown(wait=True)
        self.my_socket.close()
        logging.warning("Server socket and thread pool closed.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s - %(message)s')
    server = Server(8889)
    try:
        server.start()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nServer stopped.")
