from socket import *
import socket
import threading
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from http import Http

UPLOAD_DIR = "files"

class Server:
    def __init__(self, portnumber):
        self.portnumber = portnumber
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.executor = ThreadPoolExecutor(max_workers=10)

    def start(self):
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
                
                self.executor.submit(self.handle_client, conn, addr)
                
            except KeyboardInterrupt:
                logging.warning("Server shutting down.")
                break
            except Exception as e:
                logging.error(f"Error accepting connections: {e}")
        
        self.shutdown()

    def handle_client(self, conn, addr):
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