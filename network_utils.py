import json
import sys

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5555
connected_clients = []
connected_players = []
client_socket_lookup = {}
def send_json(client_socket, data):
    """Encodes and sends JSON data over a socket."""
    try:
        json_data = json.dumps(data) + "\n"  
        client_socket.sendall(json_data.encode('utf-8'))
        print(f"[DEBUG] Sent JSON data: {json_data}")
    except Exception as e:
        print(f"[ERROR] Failed to send JSON: {e}")

def receive_json(client_socket):
    """Receives and decodes JSON data from a socket, handling connection loss properly."""
    buffer = ""
    while True:
        try:
            chunk = client_socket.recv(4096).decode('utf-8')
            if not chunk:
                raise ConnectionAbortedError("[ERROR] Lost connection to server.")
            buffer += chunk

            messages = buffer.split("\n")
            for msg in messages[:-1]:  
                print(f"[DEBUG] Received raw message: {msg}")
                return json.loads(msg)

            buffer = messages[-1]
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON decode error: {e} (Raw message: {buffer})")
            continue
        except ConnectionAbortedError:
            print("[ERROR] Connection was closed by the server.")
            sys.exit(0)
        except ConnectionResetError:
            print("[ERROR] Connection reset by peer.")
            sys.exit(0)
def receive_message(client_socket):
    """Receives a message from a socket and determines if it is JSON or plain text."""
    buffer = ""
    while True:
        try:
            chunk = client_socket.recv(4096).decode('utf-8')
            if not chunk:
                raise ConnectionAbortedError("[ERROR] Lost connection to client.")
            buffer += chunk

            messages = buffer.split("\n")
            for msg in messages[:-1]:
                print(f"[DEBUG] Server received raw message: {msg}")
                try:
                    json_msg = json.loads(msg)
                    print(f"[DEBUG] Parsed JSON message: {json_msg}")
                    return json_msg  #If JSON, return as a dictionary
                except json.JSONDecodeError:
                    print(f"[DEBUG] Received raw text: {msg.strip()}")
                    return msg.strip()  #Otherwise, return plain string

            buffer = messages[-1]
        except ConnectionAbortedError:
            print("[ERROR] Connection was closed by the client.")
            return None
        except ConnectionResetError:
            print("[ERROR] Connection reset by peer.")
            return None
def send_to_server(client_socket, message):
    """Sends a raw message (text or JSON) to the server."""
    try:
        if isinstance(message, dict):  
            json_data = json.dumps(message) + "\n"
            client_socket.sendall(json_data.encode('utf-8'))
            print(f"[DEBUG] Sent JSON to server: {json_data}")  #   Debug sent JSON
        else:  #   Otherwise, send as raw text
            message = message.strip() + "\n"
            client_socket.sendall(message.encode('utf-8'))
            print(f"[DEBUG] Sent raw message to server: {message}")  #   Debug sent raw text
    except Exception as e:
        print(f"[ERROR] Failed to send to server: {e}")
def send_to_player(player_name, message):
    """Sends a JSON message to a player by their name."""
    client_socket = client_socket_lookup.get(player_name)
    if client_socket:
        send_to_client(client_socket, message)
    else:
        print(f"[ERROR] No client socket found for player: {player_name}")
def send_to_client(client_socket, message):
    """Sends a JSON message to a specific client."""
    try:
        json_data = json.dumps(message) + "\n"
        client_socket.sendall(json_data.encode('utf-8'))
        print(f"[DEBUG] Sent to client: {json_data}")
    except Exception as e:
        print(f"[ERROR] Failed to send to client: {e}")
def send_to_all(message):
    """Sends a JSON message to all connected clients."""
    global connected_clients
    if not message:
        print("[ERROR] send_to_all() was called without a message!")
        return
    print(f"[DEBUG] send_to_all() called with: {message}")
    for client_socket, _ in connected_clients:
        try:
            send_json(client_socket, message)
        except Exception as e:
            print(f"[ERROR] Failed to send to client {client_socket}: {e}")
