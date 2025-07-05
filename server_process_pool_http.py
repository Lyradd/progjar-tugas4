from socket import *
import socket
import logging
import multiprocessing
import os
from http import Http

# Direktori untuk file, harus sama dengan yang di http.py
UPLOAD_DIR = "files"

class ProcessTheClient(multiprocessing.Process):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        multiprocessing.Process.__init__(self)

    def run(self):
        try:
            # Membuat instance Http untuk setiap proses
            http_handler = Http()
            http_handler.process(self.connection, self.address)
        except Exception as e:
            logging.error(f"Error in process for {self.address}: {e}")
        finally:
            self.connection.close()


class Server:
    def __init__(self, portnumber):
        self.portnumber = portnumber
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        # Memastikan direktori upload ada sebelum server mulai
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)
            logging.info(f"Created directory: {UPLOAD_DIR}")
            
        self.my_socket.bind(('0.0.0.0', self.portnumber))
        self.my_socket.listen(5)
        logging.warning(f"Server (Process Pool) listening on port {self.portnumber}")

        # Menggunakan pool dari proses untuk menangani klien
        with multiprocessing.Pool(processes=5) as pool:
            while True:
                try:
                    connection, address = self.my_socket.accept()
                    logging.warning(f"Connection from {address}")
                    
                    # Membuat proses baru untuk menangani klien
                    client_process = ProcessTheClient(connection, address)
                    client_process.start()
                    self.the_clients.append(client_process)

                except KeyboardInterrupt:
                    logging.warning("Server shutting down.")
                    break
                except Exception as e:
                    logging.error(f"Error accepting connections: {e}")
        
        self.shutdown()

    def shutdown(self):
        # Menunggu semua proses anak selesai
        for client in self.the_clients:
            client.join()
        self.my_socket.close()
        logging.warning("Server socket closed.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s - %(message)s')
    server = Server(8889)
    try:
        server.start()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nServer stopped.")
