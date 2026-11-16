# Ishlatish: python DialogLokal.py
# Terminal rejimi: python DialogLokal.py server
#                 python DialogLokal.py client <server_ip>

import json
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

PORT = 5000
DISCOVERY_PORT = 5001
BUFFER = 4096
MAX_PACKET_SIZE = 8192
MAX_CLIENT_NAME_LENGTH = 30
DISCOVERY_REQUEST = b"LOCAL_CHAT_DISCOVER"
DISCOVERY_RESPONSE = b"LOCAL_CHAT_SERVER"


def _send_packet(connection, packet):
    data = json.dumps(packet, ensure_ascii=False).encode("utf-8") + b"\n"
    connection.sendall(data)


def _receive_line(connection):
    line = bytearray()
    while len(line) <= MAX_PACKET_SIZE:
        byte = connection.recv(1)
        if not byte:
            raise ConnectionError("Ulanish ro'yxatdan o'tish vaqtida uzildi.")
        if byte == b"\n":
            return bytes(line)
        line.extend(byte)
    raise ValueError("Tarmoq xabari ruxsat etilgan hajmdan katta.")


class LocalChatForm:
    def __init__(self, root):
        self.root = root
        self.root.title("Mahalliy tarmoq chat")
        self.root.geometry("740x700")
        self.root.minsize(620, 600)

        self.connection = None
        self.server_socket = None
        self.discovery_socket = None
        self.clients = {}
        self.clients_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.closing = False
        self.servers = {}

        self._build_form()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_form(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        ttk.Label(
            main, text="Mahalliy tarmoq chat", font=("Segoe UI", 18, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        network = ttk.LabelFrame(main, text="Ulanish", padding=12)
        network.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        network.columnconfigure(1, weight=1)

        ttk.Label(network, text="Ismingiz:").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 8)
        )
        self.username_entry = ttk.Entry(network)
        self.username_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Button(
            network, text="Server bo'lib kutish", command=self.start_server
        ).grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 8))
        self.server_status = ttk.Label(
            network, text="Server ishga tushirilmagan"
        )
        self.server_status.grid(row=1, column=1, sticky="w", pady=(0, 8))

        ttk.Button(
            network, text="Serverni avtomatik qidirish", command=self.search_servers
        ).grid(row=2, column=0, sticky="ew", padx=(0, 10))
        self.search_status = ttk.Label(
            network, text="Bir xil Wi-Fi/LAN tarmog'idagi serverlar topiladi"
        )
        self.search_status.grid(row=2, column=1, sticky="w")

        self.server_list = tk.Listbox(network, height=4, exportselection=False)
        self.server_list.grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(10, 8)
        )
        self.server_list.bind("<<ListboxSelect>>", self._on_server_selected)

        self.connect_button = ttk.Button(
            network, text="Ro'yxatdan o'tish va ulanish",
            command=self.connect_to_selected, state="disabled"
        )
        self.connect_button.grid(row=4, column=0, sticky="w")

        self.chat_status = ttk.Label(network, text="Ulanish kutilmoqda")
        self.chat_status.grid(row=4, column=1, sticky="w")

        clients_frame = ttk.LabelFrame(
            main, text="Serverga ulangan klientlar", padding=8
        )
        clients_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self.client_list = tk.Listbox(
            clients_frame, height=3, exportselection=False
        )
        self.client_list.pack(fill="x")

        chat_frame = ttk.LabelFrame(main, text="Suhbat", padding=10)
        chat_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        chat_frame.rowconfigure(0, weight=1)
        chat_frame.columnconfigure(0, weight=1)

        self.chat_log = tk.Text(
            chat_frame, state="disabled", wrap="word", font=("Segoe UI", 10)
        )
        self.chat_log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            chat_frame, orient="vertical", command=self.chat_log.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_log.configure(yscrollcommand=scrollbar.set)

        send_frame = ttk.Frame(main)
        send_frame.grid(row=4, column=0, sticky="ew")
        send_frame.columnconfigure(0, weight=1)
        self.message_entry = ttk.Entry(send_frame)
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.message_entry.bind("<Return>", self.send_message)
        self.send_button = ttk.Button(
            send_frame, text="Yuborish", command=self.send_message, state="disabled"
        )
        self.send_button.grid(row=0, column=1)

    def start_server(self):
        if self.server_socket is not None:
            return

        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp_socket.bind(("0.0.0.0", PORT))
            tcp_socket.listen()
            tcp_socket.settimeout(0.5)

            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.bind(("0.0.0.0", DISCOVERY_PORT))
            udp_socket.settimeout(0.5)
        except OSError as error:
            tcp_socket.close()
            udp_socket.close()
            messagebox.showerror("Server xatosi", str(error), parent=self.root)
            return

        self.server_socket = tcp_socket
        self.discovery_socket = udp_socket
        self.stop_event.clear()
        self.server_status.configure(
            text=f"Server tayyor: barcha tarmoq adapterlarida, port {PORT}"
        )
        self._append_message("Tizim", "Server ishga tushdi.")
        threading.Thread(
            target=self._accept_connections, args=(tcp_socket,), daemon=True
        ).start()
        threading.Thread(
            target=self._answer_discovery, args=(udp_socket,), daemon=True
        ).start()

    def _accept_connections(self, server_socket):
        while not self.stop_event.is_set():
            try:
                connection, _ = server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            connection.settimeout(5)
            try:
                registration = json.loads(
                    _receive_line(connection).decode("utf-8")
                )
                if not isinstance(registration, dict):
                    raise ValueError("Ro'yxatdan o'tish ma'lumoti noto'g'ri.")
                name = registration.get("name")
                if (
                    registration.get("type") != "register"
                    or not isinstance(name, str)
                ):
                    raise ValueError("Klient ro'yxatdan o'tish ma'lumotini yubormadi.")
                name = name.strip()
                if not name or len(name) > MAX_CLIENT_NAME_LENGTH:
                    raise ValueError("Klient ismi bo'sh yoki juda uzun.")
            except (ConnectionError, OSError, UnicodeDecodeError, json.JSONDecodeError,
                    ValueError) as error:
                try:
                    _send_packet(
                        connection, {"type": "error", "message": str(error)}
                    )
                except OSError:
                    pass
                connection.close()
                continue

            with self.clients_lock:
                duplicate = any(
                    registered_name.casefold() == name.casefold()
                    for registered_name in self.clients.values()
                )
                if not duplicate:
                    self.clients[connection] = name

            if duplicate:
                try:
                    _send_packet(
                        connection,
                        {"type": "error", "message": "Bu ism allaqachon ro'yxatdan o'tgan."}
                    )
                except OSError:
                    pass
                connection.close()
                continue

            try:
                _send_packet(connection, {"type": "registered", "name": name})
            except OSError:
                self._remove_client(connection)
                continue
            connection.settimeout(None)
            self._schedule(self._client_list_changed)
            self._schedule(
                self._append_message, "Tizim", f"{name} klient sifatida ro'yxatdan o'tdi."
            )
            self._broadcast_client_list()
            threading.Thread(
                target=self._serve_client, args=(connection,), daemon=True
            ).start()

    def _serve_client(self, connection):
        pending = b""
        try:
            while not self.stop_event.is_set():
                data = connection.recv(BUFFER)
                if not data:
                    break
                pending += data
                while b"\n" in pending:
                    line, pending = pending.split(b"\n", 1)
                    packet = json.loads(line.decode("utf-8"))
                    if not isinstance(packet, dict):
                        raise ValueError("Klient xabari noto'g'ri formatda.")
                    if packet.get("type") != "message":
                        raise ValueError("Noma'lum tarmoq xabari turi.")
                    message = packet.get("message")
                    if not isinstance(message, str) or not message.strip():
                        continue
                    with self.clients_lock:
                        name = self.clients.get(connection)
                    if name is None:
                        return
                    self._schedule(self._append_message, name, message)
                    self._send_to_clients(
                        {"type": "message", "name": name, "message": message},
                        exclude=connection
                    )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            if not self.stop_event.is_set():
                self._schedule(
                    self._append_message, "Tizim", f"Klient xabari xatosi: {error}"
                )
        finally:
            self._remove_client(connection)

    def _remove_client(self, connection):
        with self.clients_lock:
            name = self.clients.pop(connection, None)
            client_names = list(self.clients.values())
        if name is None:
            connection.close()
            return
        connection.close()
        self._schedule(self._client_list_changed, client_names)
        self._schedule(
            self._append_message, "Tizim", f"{name} klienti uzildi."
        )
        self._broadcast_client_list(client_names)

    def _client_list_changed(self, client_names=None):
        if self.closing:
            return
        if client_names is None:
            with self.clients_lock:
                client_names = list(self.clients.values())
        self.client_list.delete(0, tk.END)
        for name in sorted(client_names, key=str.casefold):
            self.client_list.insert(tk.END, name)

    def _broadcast_client_list(self, client_names=None):
        if client_names is None:
            with self.clients_lock:
                client_names = list(self.clients.values())
        self._send_to_clients({"type": "clients", "names": client_names})

    def _send_to_clients(self, packet, exclude=None):
        with self.clients_lock:
            connections = [
                client for client in self.clients if client is not exclude
            ]
        failed = []
        for client in connections:
            try:
                _send_packet(client, packet)
            except OSError:
                failed.append(client)
        for client in failed:
            self._remove_client(client)

    def _answer_discovery(self, discovery_socket):
        while not self.stop_event.is_set():
            try:
                data, address = discovery_socket.recvfrom(BUFFER)
            except socket.timeout:
                continue
            except OSError:
                break

            if data == DISCOVERY_REQUEST:
                try:
                    discovery_socket.sendto(DISCOVERY_RESPONSE, address)
                except OSError:
                    if not self.stop_event.is_set():
                        self._schedule(
                            self._append_message,
                            "Tizim",
                            "Server qidiruv javobini yubora olmadi."
                        )

    def search_servers(self):
        self.servers.clear()
        self.server_list.delete(0, tk.END)
        self.connect_button.configure(state="disabled")
        self.search_status.configure(text="Tarmoq skanerlanmoqda...")
        threading.Thread(target=self._scan_network, daemon=True).start()

    def _scan_network(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as scan_socket:
                scan_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                scan_socket.settimeout(0.25)
                start = time.monotonic()
                next_request = 0.0
                while time.monotonic() - start < 4.0:
                    elapsed = time.monotonic() - start
                    if elapsed >= next_request:
                        scan_socket.sendto(
                            DISCOVERY_REQUEST, ("255.255.255.255", DISCOVERY_PORT)
                        )
                        next_request = elapsed + 0.5
                    try:
                        data, address = scan_socket.recvfrom(BUFFER)
                    except socket.timeout:
                        continue
                    if data == DISCOVERY_RESPONSE and address[0] not in self.servers:
                        self.servers[address[0]] = f"{address[0]}:{PORT}"
                        self._schedule(self._add_server, address[0])
        except OSError as error:
            self._schedule(self._scan_finished, f"Qidiruv xatosi: {error}")
            return

        self._schedule(self._scan_finished, None)

    def _add_server(self, host):
        if not self.closing and host in self.servers:
            self.server_list.insert(tk.END, self.servers[host])

    def _scan_finished(self, error):
        if error:
            self.search_status.configure(text=error)
        elif self.servers:
            self.search_status.configure(
                text=f"{len(self.servers)} ta server topildi."
            )
        else:
            self.search_status.configure(
                text="Server topilmadi. U bir xil LAN'da va yoqilganligini tekshiring."
            )

    def _on_server_selected(self, event):
        _ = event
        state = "normal" if self.server_list.curselection() else "disabled"
        self.connect_button.configure(state=state)

    def connect_to_selected(self):
        selection = self.server_list.curselection()
        if not selection:
            return
        name = self.username_entry.get().strip()
        if not name or len(name) > MAX_CLIENT_NAME_LENGTH:
            messagebox.showwarning(
                "Ism kerak",
                f"Ismingizni kiriting (1-{MAX_CLIENT_NAME_LENGTH} belgi).",
                parent=self.root
            )
            self.username_entry.focus_set()
            return
        if self.connection is not None:
            messagebox.showinfo(
                "Ulangan", "Avval joriy ulanishni uzing.", parent=self.root
            )
            return
        host = self.server_list.get(selection[0]).split(":")[0]
        self.connect_button.configure(state="disabled")
        self.search_status.configure(
            text=f"{name} nomi bilan {host} serveriga ulanmoqda..."
        )
        threading.Thread(
            target=self._connect_to_server, args=(host, name), daemon=True
        ).start()

    def _connect_to_server(self, host, name):
        connection = None
        try:
            connection = socket.create_connection((host, PORT), timeout=5)
            connection.settimeout(5)
            _send_packet(connection, {"type": "register", "name": name})
            response = json.loads(_receive_line(connection).decode("utf-8"))
            if not isinstance(response, dict):
                raise ValueError("Serverdan noto'g'ri javob keldi.")
            if response.get("type") != "registered":
                raise ValueError(
                    response.get("message", "Server ro'yxatdan o'tkazmadi.")
                )
            connection.settimeout(None)
        except OSError as error:
            if connection is not None:
                connection.close()
            self._schedule(
                self._connect_failed, f"{host} serveriga ulanib bo'lmadi: {error}"
            )
            return
        except (ConnectionError, UnicodeDecodeError, json.JSONDecodeError,
                ValueError) as error:
            if connection is not None:
                connection.close()
            self._schedule(self._connect_failed, str(error))
            return

        if self.closing:
            connection.close()
            return
        self.connection = connection
        self._schedule(self._connection_ready, f"Ulandi: {host} ({name})")
        threading.Thread(
            target=self._receive_messages, args=(connection,), daemon=True
        ).start()

    def _receive_messages(self, connection):
        pending = b""
        try:
            while not self.stop_event.is_set():
                data = connection.recv(BUFFER)
                if not data:
                    break
                pending += data
                while b"\n" in pending:
                    line, pending = pending.split(b"\n", 1)
                    packet = json.loads(line.decode("utf-8"))
                    if not isinstance(packet, dict):
                        raise ValueError("Serverdan noto'g'ri xabar keldi.")
                    if packet.get("type") == "message":
                        name = packet.get("name", "Qarshi tomon")
                        message = packet.get("message", "")
                        if not isinstance(name, str) or not isinstance(message, str):
                            raise ValueError("Serverdan noto'g'ri chat xabari keldi.")
                        self._schedule(
                            self._append_message,
                            name,
                            message
                        )
                    elif packet.get("type") == "clients":
                        names = packet.get("names", [])
                        if isinstance(names, list) and all(
                            isinstance(name, str) for name in names
                        ):
                            self._schedule(self._client_list_changed, names)
                    elif packet.get("type") == "error":
                        self._schedule(
                            self._append_message,
                            "Tizim",
                            packet.get("message", "Server xabari xatosi.")
                        )
                    else:
                        raise ValueError("Server noma'lum xabar yubordi.")
            if pending:
                raise ValueError("Server to'liq bo'lmagan xabar yubordi.")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            if not self.stop_event.is_set():
                self._schedule(self._append_message, "Tizim", f"Ulanish xatosi: {error}")
        finally:
            connection.close()
            if self.connection is connection:
                self.connection = None
                self._schedule(self._connection_closed)

    def send_message(self, event=None):
        _ = event
        connection = self.connection
        message = self.message_entry.get().strip()
        if connection is None or not message:
            return
        try:
            _send_packet(
                connection, {"type": "message", "message": message}
            )
        except OSError as error:
            messagebox.showerror("Yuborish xatosi", str(error), parent=self.root)
            return
        self.message_entry.delete(0, tk.END)
        self._append_message("Siz", message)

    def _connection_ready(self, status):
        if self.closing:
            return
        self.chat_status.configure(text=status)
        self.send_button.configure(state="normal")
        self.connect_button.configure(state="disabled")
        self.message_entry.focus_set()

    def _connection_closed(self):
        if self.closing:
            return
        self.chat_status.configure(text="Ulanish uzildi")
        self.send_button.configure(state="disabled")
        if self.server_list.curselection():
            self.connect_button.configure(state="normal")
        self._append_message("Tizim", "Ulanish uzildi.")

    def _connect_failed(self, error):
        self.search_status.configure(text=error)
        self.connect_button.configure(
            state="normal" if self.server_list.curselection() else "disabled"
        )

    def _append_message(self, sender, message):
        if self.closing:
            return
        self.chat_log.configure(state="normal")
        self.chat_log.insert(tk.END, f"{sender}: {message}\n")
        self.chat_log.see(tk.END)
        self.chat_log.configure(state="disabled")

    def _schedule(self, callback, *args):
        if self.closing:
            return
        try:
            self.root.after(0, callback, *args)
        except tk.TclError:
            if not self.closing:
                raise

    def close(self):
        self.closing = True
        self.stop_event.set()
        with self.clients_lock:
            client_connections = list(self.clients)
        for network_socket in (
            self.connection, self.server_socket, self.discovery_socket,
            *client_connections
        ):
            if network_socket is not None:
                try:
                    network_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                network_socket.close()
        self.root.destroy()


def server_mode():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", PORT))
    server_socket.listen(1)
    print(f"Server ishga tushdi. Port: {PORT}")
    print("Boshqa kompyuter ulanishini kutyapman...")
    connection, address = server_socket.accept()
    print(f"Ulandi: {address}")
    handle_connection(connection)


def client_mode(host):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.connect((host, PORT))
    print(f"Serverga ulandi: {host}:{PORT}")
    handle_connection(connection)


def handle_connection(connection):
    def receiver():
        pending = b""
        while True:
            try:
                data = connection.recv(BUFFER)
                if not data:
                    print("\nUlanish uzildi.")
                    break
                pending += data
                while b"\n" in pending:
                    message, pending = pending.split(b"\n", 1)
                    print(f"\nQarshi tomon: {message.decode('utf-8')}")
                    print("Siz: ", end="", flush=True)
            except OSError:
                break
        if pending:
            print(f"\nQarshi tomon: {pending.decode('utf-8', errors='replace')}")

    threading.Thread(target=receiver, daemon=True).start()

    try:
        while True:
            message = input("Siz: ")
            if message.lower() in ("exit", "quit", "chiqish"):
                connection.sendall("Ulanish tugatildi.\n".encode("utf-8"))
                break
            connection.sendall(message.encode("utf-8") + b"\n")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        connection.close()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        root = tk.Tk()
        LocalChatForm(root)
        root.mainloop()
    else:
        mode = sys.argv[1].lower()
        if mode == "server":
            server_mode()
        elif mode == "client":
            if len(sys.argv) < 3:
                print("Server IP manzilini kiriting: python DialogLokal.py client <ip>")
                sys.exit(1)
            client_mode(sys.argv[2])
        else:
            print("Noto'g'ri rejim. 'server' yoki 'client' bo'lishi kerak.")
            sys.exit(1)
