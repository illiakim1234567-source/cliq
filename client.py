import socket
import json

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

with open("data.json", "r") as f:
    data = json.load(f)

def register():
    nickname = input("Enter your nickname: ")

    while len(nickname) < 3 or len(nickname) > 20:
        print("Nickname must be between 3 and 20 characters!")
        nickname = input("Enter your nickname: ")

    data["nickname"] = nickname

    password = input("Enter your password: ")

    while len(password) < 4 or len(password) > 20:
        print("Password must be between 4 and 20 characters!")
        password = input("Enter your password: ")

    data["password"] = password

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if data["nickname"] != "":
    password = input("Enter your password: ")

    while data["password"] != password:
        print("Password is incorrect!")
        password = input("Enter your password: ")

    print("Login completed.")

else:
    register()

connected = False
ip = ""
port = ""

while not connected:
    ip = input("Enter server IP: ")
    port = input("Enter server port: ")

    try:
        client.connect((ip, int(port)))
        connected = True
        print("Connected successfully.")

    except ValueError:
        print("Port must be a number!")
        continue

    except (socket.gaierror, ConnectionRefusedError):
        print("Cannot connect to the server!")
        continue
