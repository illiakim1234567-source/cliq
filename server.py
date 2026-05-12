import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_address = input("Enter server address: ")
port = int(input("Enter server port: "))

server.bind((server_address, port))

server.listen()

print(f"Listening on {server_address}:{port}")

while True:
    client, addr = server.accept()

    print(f"Connected: {addr}")

    data = client.recv(1024).decode()

    print(data)

    client.send("Hello client".encode())

    client.close()