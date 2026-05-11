import socket
import threading

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_address = input('Enter server address: ')
port = int(input('Enter server port: '))

server.bind((server_address, int(port)))

server.listen()
print("Listening on " + server_address)
print(f"Listening on {server_address}")