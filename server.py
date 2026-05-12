import socket
import threading
import json
import os
import time
from datetime import datetime

if os.name == "nt":
    os.system("color")

R      = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
RED    = "\033[91m"
MAGENTA= "\033[95m"
WHITE  = "\033[97m"


def fmt_time():
    return DIM + datetime.now().strftime("%H:%M:%S") + R


def log(symbol, color, text):
    print(f"{fmt_time()} {color}{BOLD}{symbol}{R} {text}")


def log_info(text):   log("•", YELLOW, text)
def log_join(text):   log("+", GREEN,  text)
def log_leave(text):  log("−", YELLOW, text)
def log_new(text):    log("★", CYAN,   text)
def log_msg(text):    log("»", WHITE,  text)
def log_error(text):  log("✖", RED,    text)
def log_cmd(text):    log("⚡", MAGENTA, text)


def divider(label=""):
    width = 52
    if label:
        pad = (width - len(label) - 2) // 2
        print(f"{DIM}{'─' * pad} {label} {'─' * pad}{R}")
    else:
        print(f"{DIM}{'─' * width}{R}")


def banner(host, port):
    print(f"""
{CYAN}{BOLD}  ██████╗██╗     ██╗ ██████╗
 ██╔════╝██║     ██║██╔═══██╗
 ██║     ██║     ██║██║   ██║
 ██║     ██║     ██║██║▄▄ ██║
 ╚██████╗███████╗██║╚██████╔╝
  ╚═════╝╚══════╝╚═╝ ╚══▀▀═╝ {R}{DIM}Server{R}
""")
    divider("Config")
    print(f"  {DIM}Host:{R} {CYAN}{host}{R}")
    print(f"  {DIM}Port:{R} {CYAN}{port}{R}")
    divider("Commands")
    print(f"  {DIM}list{R}              — show online users")
    print(f"  {DIM}kick   <nickname>{R} — kick user")
    print(f"  {DIM}ban    <nickname>{R} — ban user")
    print(f"  {DIM}unban  <nickname>{R} — unban user")
    print(f"  {DIM}mute   <nickname>{R} — mute user")
    print(f"  {DIM}unmute <nickname>{R} — unmute user")
    divider()
    print()


HOST = "0.0.0.0"
PORT = int(input(f"  {DIM}Port:{R} "))

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

clients = {}
banned  = set()
muted   = set()
lock    = threading.Lock()

USERS_FILE = "users.json"


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(u):
    with open(USERS_FILE, "w") as f:
        json.dump(u, f, indent=2)


users = load_users()


def send(conn, obj):
    try:
        conn.sendall((json.dumps(obj) + "\n").encode())
        return True
    except:
        return False


def broadcast(obj):
    with lock:
        targets = list(clients.values())
    for c in targets:
        send(c, obj)


def recv_line(conn):
    buf = b""
    while True:
        ch = conn.recv(1)
        if not ch:
            return None
        if ch == b"\n":
            return buf.decode()
        buf += ch


def kick_user(nickname, reason):
    with lock:
        conn = clients.get(nickname)
    if conn:
        send(conn, {"type": "kick", "text": reason})
        time.sleep(0.3)
        conn.close()


def handle_client(conn, addr):
    nickname = ""
    try:
        send(conn, {"type": "handshake"})

        line = recv_line(conn)
        if not line:
            conn.close()
            return

        data     = json.loads(line)
        nickname = data.get("nickname", "").strip()
        password = data.get("password", "").strip()

        if not nickname or not password:
            send(conn, {"type": "error", "text": "empty credentials"})
            conn.close()
            return

        with lock:
            if nickname in banned:
                send(conn, {"type": "error", "text": "You are banned on this server."})
                time.sleep(0.2)
                conn.close()
                return

            if nickname in users:
                if users[nickname] != password:
                    send(conn, {"type": "error", "text": "Wrong password."})
                    time.sleep(0.2)
                    conn.close()
                    return
            else:
                users[nickname] = password
                save_users(users)
                log_new(f"New user registered: {CYAN}{BOLD}{nickname}{R}")

            if nickname in clients:
                send(conn, {"type": "error", "text": "Already online."})
                time.sleep(0.2)
                conn.close()
                return

            clients[nickname] = conn

        send(conn, {"type": "system", "text": "ok"})
        broadcast({"type": "system", "text": f"{nickname} joined."})
        log_join(f"{CYAN}{BOLD}{nickname}{R} {DIM}({addr[0]}:{addr[1]}){R}")

        while True:
            line = recv_line(conn)
            if line is None:
                break

            data = json.loads(line)

            if data.get("type") == "message":
                text = data.get("text", "").strip()
                if not text:
                    continue

                with lock:
                    is_muted = nickname in muted

                if is_muted:
                    send(conn, {"type": "system", "text": "You are muted."})
                    continue

                log_msg(f"{CYAN}{BOLD}[{nickname}]{R} {text}")
                broadcast({"type": "message", "from": nickname, "text": text})

    except Exception as e:
        s = str(e)
        if "10053" not in s and "10054" not in s:
            log_error(f"{nickname or addr}: {e}")
    finally:
        with lock:
            clients.pop(nickname, None)
        try:
            conn.close()
        except:
            pass
        if nickname:
            log_leave(f"{CYAN}{BOLD}{nickname}{R} left.")
            broadcast({"type": "system", "text": f"{nickname} left."})


def accept_loop():
    while True:
        try:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except:
            break


def command_loop():
    while True:
        try:
            raw = input(f"{DIM}>{R} ")
        except EOFError:
            break

        parts = raw.strip().split(maxsplit=1)
        if not parts:
            continue

        action = parts[0]

        if action == "list":
            with lock:
                online = list(clients.keys())
            if online:
                log_info(f"Online ({len(online)}): " + ", ".join(f"{CYAN}{n}{R}" for n in online))
            else:
                log_info("No users online.")
            continue

        if len(parts) < 2:
            log_error("Usage: <command> <nickname>.")
            continue

        target = parts[1]

        with lock:
            conn = clients.get(target)

        if action == "kick":
            if not conn:
                log_error(f"{target} is not online.")
                continue
            kick_user(target, "You have been kicked.")
            log_cmd(f"Kicked {CYAN}{BOLD}{target}{R}.")

        elif action == "ban":
            banned.add(target)
            log_cmd(f"Banned {CYAN}{BOLD}{target}{R}.")
            if conn:
                kick_user(target, "You have been banned from this server.")

        elif action == "unban":
            banned.discard(target)
            log_cmd(f"Unbanned {CYAN}{BOLD}{target}{R}.")

        elif action == "mute":
            if not conn:
                log_error(f"{target} is not online.")
                continue
            muted.add(target)
            send(conn, {"type": "system", "text": "You have been muted."})
            log_cmd(f"Muted {CYAN}{BOLD}{target}{R}.")

        elif action == "unmute":
            muted.discard(target)
            with lock:
                conn = clients.get(target)
            if conn:
                send(conn, {"type": "system", "text": "You have been unmuted."})
            log_cmd(f"Unmuted {CYAN}{BOLD}{target}{R}.")

        else:
            log_error(f"Unknown command: {action}.")


banner(HOST, PORT)
threading.Thread(target=accept_loop, daemon=True).start()
command_loop()