import socket
import threading
import json

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

with open("banned.json", "r", encoding="utf-8") as f:
    data = json.load(f)

banned = set(data.get("banned", []))
muted = set()
clients = {}

server.bind(("0.0.0.0", 5555))
server.listen()


def save_bans():
    with open("banned.json", "w", encoding="utf-8") as f:
        json.dump({"banned": list(banned)}, f, ensure_ascii=False, indent=4)


def send(conn, obj):
    try:
        conn.send(json.dumps(obj).encode())
    except:
        pass


def broadcast(obj, skip=None):
    for c in list(clients.values()):
        if c != skip:
            send(c, obj)


def handle_client(conn):
    nickname = ""

    try:
        conn.send("NICK".encode())

        msg = conn.recv(1024).decode()
        data_msg = json.loads(msg)

        if data_msg["type"] == "nick":
            nickname = data_msg["nickname"]

        if nickname in banned:
            send(conn, {"type": "system", "text": "banned"})
            conn.close()
            return

        clients[nickname] = conn

        broadcast({"type": "system", "text": f"{nickname} joined"})

        while True:
            try:
                msg = conn.recv(1024).decode()
                if not msg:
                    break

                data_msg = json.loads(msg)

                if data_msg["type"] == "message":
                    if nickname in muted:
                        continue

                    broadcast({
                        "type": "message",
                        "from": nickname,
                        "text": data_msg["text"]
                    }, skip=conn)

            except:
                break

    finally:
        if nickname in clients:
            del clients[nickname]

        conn.close()

        if nickname:
            broadcast({"type": "system", "text": f"{nickname} left"})


def accept_clients():
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()


def handle_command(cmd):
    parts = cmd.split()

    if len(parts) < 2:
        return

    action = parts[0]
    target = parts[1]

    if action == "list":
        print(list(clients.keys()))
        return

    if target not in clients:
        return

    conn = clients[target]

    if action == "kick":
        send(conn, {"type": "system", "text": "kicked"})
        conn.close()
        del clients[target]

    elif action == "ban":
        banned.add(target)
        save_bans()
        send(conn, {"type": "system", "text": "banned"})
        conn.close()
        del clients[target]

    elif action == "mute":
        muted.add(target)


def command_loop():
    while True:
        cmd = input("> ")
        handle_command(cmd)


threading.Thread(target=accept_clients, daemon=True).start()
command_loop()