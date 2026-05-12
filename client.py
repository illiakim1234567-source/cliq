import socket
import threading
import json
import sys
import os
import getpass
from datetime import datetime

try:
    import readline
    HAS_READLINE = True
except ImportError:
    try:
        import pyreadline3 as readline
        HAS_READLINE = True
    except ImportError:
        HAS_READLINE = False

if sys.platform == "win32":
    os.system("color")

ACCOUNT_FILE = "account.json"
print_lock = threading.Lock()

R  = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"

CYAN    = "\033[96m"
YELLOW  = "\033[93m"
GREEN   = "\033[92m"
RED     = "\033[91m"
MAGENTA = "\033[95m"
BLUE    = "\033[94m"
WHITE   = "\033[97m"

NICK_COLORS = [CYAN, MAGENTA, YELLOW, GREEN, BLUE, WHITE]
nick_color_map = {}
nick_color_index = 0


def get_nick_color(nick):
    global nick_color_index
    if nick not in nick_color_map:
        nick_color_map[nick] = NICK_COLORS[nick_color_index % len(NICK_COLORS)]
        nick_color_index += 1
    return nick_color_map[nick]


def fmt_time():
    return DIM + datetime.now().strftime("%H:%M") + R


def fmt_system(text):
    text = text.strip()
    if text:
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?":
            text += "."
    return f"{fmt_time()} {YELLOW}•{R} {DIM}{text}{R}"


def fmt_error(text):
    text = text.strip()
    if text:
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?":
            text += "!"
    return f"{fmt_time()} {RED}✖{R} {RED}{text}{R}"


def fmt_kick(text):
    text = text.strip()
    if text:
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?":
            text += "!"
    return f"{fmt_time()} {RED}⚠  {text}{R}"


def fmt_message(sender, text, is_self=False):
    color = CYAN if is_self else get_nick_color(sender)
    label = "You" if is_self else sender
    return f"{fmt_time()} {color}{BOLD}[{label}]{R} {text}"


def banner():
    print(f"""
{CYAN}{BOLD}  ██████╗██╗     ██╗ ██████╗
 ██╔════╝██║     ██║██╔═══██╗
 ██║     ██║     ██║██║   ██║
 ██║     ██║     ██║██║▄▄ ██║
 ╚██████╗███████╗██║╚██████╔╝
  ╚═════╝╚══════╝╚═╝ ╚══▀▀═╝ {R}{DIM}Chat client{R}
""")


def divider(label=""):
    width = 48
    if label:
        pad = (width - len(label) - 2) // 2
        print(f"{DIM}{'─' * pad} {label} {'─' * pad}{R}")
    else:
        print(f"{DIM}{'─' * width}{R}")


def load_account():
    if os.path.exists(ACCOUNT_FILE):
        with open(ACCOUNT_FILE, "r") as f:
            return json.load(f)
    return None


def save_account(nickname, password):
    with open(ACCOUNT_FILE, "w") as f:
        json.dump({"nickname": nickname, "password": password}, f)


def setup_account():
    account = load_account()
    if account:
        divider("Account")
        print(f"  {DIM}Found account:{R} {CYAN}{BOLD}{account['nickname']}{R}")
        print(f"  {GREEN}1{R} — Use this account")
        print(f"  {YELLOW}2{R} — Create new account")
        divider()
        if input(f"{DIM}>{R} ").strip() == "1":
            return account["nickname"], account["password"]

    divider("Create account")
    while True:
        nickname = input(f"  {DIM}Nickname:{R} ").strip()
        if nickname:
            break
        print(fmt_error("Nickname cannot be empty."))

    while True:
        password = getpass.getpass(f"  {DIM}Password:{R} ")
        confirm  = getpass.getpass(f"  {DIM}Confirm: {R} ")
        if password and password == confirm:
            break
        print(fmt_error("Passwords don't match or empty, try again."))

    save_account(nickname, password)
    divider()
    print(fmt_system(f"Account saved as {CYAN}{BOLD}{nickname}{R}{DIM}."))
    return nickname, password


def print_above(text):
    with print_lock:
        if HAS_READLINE:
            buf = readline.get_line_buffer() if hasattr(readline, "get_line_buffer") else ""
            sys.stdout.write("\r\033[K")
            sys.stdout.write(text + "\n")
            sys.stdout.write(f"{DIM}>{R} " + buf)
            sys.stdout.flush()
        else:
            sys.stdout.write("\r\033[K" + text + "\n")
            sys.stdout.flush()


def connect_to_server(nickname, password):
    divider("Connect")
    HOST = input(f"  {DIM}IP:  {R}").strip()
    PORT = int(input(f"  {DIM}Port:{R} "))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except Exception as e:
        print(fmt_error(f"Connection failed: {e}"))
        return None, None, None

    return sock, HOST, PORT


def run_session(sock, nickname, password, host, port):
    connected = threading.Event()
    failed    = threading.Event()
    done      = threading.Event()
    reconnect = threading.Event()

    def send(obj):
        try:
            sock.sendall((json.dumps(obj) + "\n").encode())
        except:
            pass

    def recv_line():
        buf = b""
        while True:
            ch = sock.recv(1)
            if not ch:
                return None
            if ch == b"\n":
                return buf.decode()
            buf += ch

    def recv_loop():
        while True:
            try:
                line = recv_line()
                if line is None:
                    if connected.is_set():
                        print_above(fmt_system("Disconnected from server."))
                    else:
                        failed.set()
                    break

                data = json.loads(line)
                t    = data.get("type")
                text = data.get("text", "")

                if t == "handshake":
                    send({"nickname": nickname, "password": password})

                elif t == "system":
                    if text == "ok":
                        connected.set()
                    else:
                        print_above(fmt_system(text))

                elif t == "error":
                    print_above(fmt_error(text))
                    if not connected.is_set():
                        failed.set()
                    break

                elif t == "kick":
                    print_above(fmt_kick(text))
                    reconnect.set()
                    break

                elif t == "message":
                    sender  = data.get("from", "?")
                    is_self = sender == nickname
                    print_above(fmt_message(sender, text, is_self))

            except Exception as e:
                if not done.is_set():
                    print_above(fmt_error(str(e)))
                    if not connected.is_set():
                        failed.set()
                break

        done.set()
        try:
            sock.close()
        except:
            pass

    threading.Thread(target=recv_loop, daemon=True).start()

    connected.wait(timeout=10)
    if failed.is_set() or not connected.is_set():
        return False

    divider()
    print(f"  {GREEN}{BOLD}Connected{R} to {CYAN}{host}:{port}{R} as {CYAN}{BOLD}{nickname}{R}")
    divider()
    print()

    while not done.is_set():
        try:
            text = input(f"{DIM}>{R} ")
        except (EOFError, KeyboardInterrupt):
            break

        if done.is_set():
            break

        text = text.strip()
        if not text:
            continue

        send({"type": "message", "text": text})

    done.wait(timeout=2)
    return reconnect.is_set()


def main():
    banner()
    nickname, password = setup_account()

    while True:
        sock, host, port = connect_to_server(nickname, password)
        if sock is None:
            if input(f"\n  Try again? {DIM}(y/n){R} > ").strip().lower() != "y":
                break
            continue

        want_reconnect = run_session(sock, nickname, password, host, port)

        print()
        if want_reconnect:
            prompt = f"  Connect to another server? {DIM}(y/n){R} > "
        else:
            prompt = f"  Reconnect? {DIM}(y/n){R} > "

        if input(prompt).strip().lower() != "y":
            break

    print(f"\n{DIM}Bye.{R}\n")


main()