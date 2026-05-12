import socket
import json
import threading

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)


def register():
    nickname = input("Enter your nickname: ")

    while len(nickname) < 3 or len(nickname) > 20:
        print("Nickname must be between 3 and 20 characters!")
        nickname = input("Enter your nickname: ")

    password = input("Enter your password: ")

    while len(password) < 4 or len(password) > 20:
        print("Password must be between 4 and 20 characters!")
        password = input("Enter your password: ")

    data["nickname"] = nickname
    data["password"] = password

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if data.get("nickname"):
    password = input("Enter your password: ")

    while data["password"] != password:
        print("Password is incorrect!")
        password = input("Enter your password: ")
else:
    register()

connected = False

while not connected:
    ip = input("Enter server IP: ")
    port = int(input("Enter server port: "))

    try:
        client.connect((ip, port))
        connected = True
        print("Connected successfully.")
    except:
        print("Cannot connect to server!")


def send_json(obj):
    client.send(json.dumps(obj).encode())


def receive():
    while True:
        try:
            msg = client.recv(1024).decode()
            if not msg:
                break

            data = json.loads(msg)

            if data["type"] == "message":
                print(f"{data['from']}: {data['text']}")

            if data["type"] == "system":
                print(f"[SYSTEM] {data['text']}")
        except:
            break


if client.recv(1024).decode() == "NICK":
    send_json({
        "type": "nick",
        "nickname": data["nickname"]
    })

threading.Thread(target=receive, daemon=True).start()

while True:
    text = input()
    send_json({
        "type": "message",
        "text": text
    })