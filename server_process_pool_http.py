from socket import *
import socket
import logging
import os
from http import Http
from concurrent.futures import ProcessPoolExecutor

UPLOAD_DIR = "files"

def handle_client_process(connection, address):
    """
    Fungsi ini dijalankan oleh worker process di dalam pool untuk menangani
    satu koneksi dari klien.
    """
    try:
        http_handler = Http()
        http_handler.process(connection, address)
    except Exception as e:
        logging.error(f"Error in process for {address}: {e}")
    finally:
        connection.close()


class Server:
    def __init__(self, portnumber, max_workers=5):
        self.portnumber = portnumber
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.executor = ProcessPoolExecutor(max_workers=max_workers)

    def start(self):
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)
            logging.info(f"Created directory: {UPLOAD_DIR}")
            
        self.my_socket.bind(('0.0.0.0', self.portnumber))
        self.my_socket.listen(5)
        logging.warning(f"Server (Process Pool) listening on port {self.portnumber}")

        while True:
            try:
                connection, address = self.my_socket.accept()
                logging.warning(f"Connection from {address}")
                
                self.executor.submit(handle_client_process, connection, address)

            except KeyboardInterrupt:
                logging.warning("Server shutting down.")
                break
            except Exception as e:
                logging.error(f"Error accepting connections: {e}")
        
        self.shutdown()

    def shutdown(self):
        self.executor.shutdown(wait=True)
        self.my_socket.close()
        logging.warning("Server socket and process pool closed.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s - %(message)s')
    
    server = Server(8889)
    try:
        server.start()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nServer stopped.")