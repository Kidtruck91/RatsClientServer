import json
import sys

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5555
clients = []
players = []
def send_json(client_socket, data):
    """Encodes and sends JSON data over a socket."""
    try:
        json_data = json.dumps(data) + "\n"  # Ensure newline for message boundaries
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
            for msg in messages[:-1]:  # Process complete JSON messages
                print(f"[DEBUG] Received raw message: {msg}")  # ✅ Debug received message
                return json.loads(msg)  # Parse first complete JSON object

            buffer = messages[-1]  # Keep partial message in buffer
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON decode error: {e} (Raw message: {buffer})")
            continue  # Wait for more data
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
            for msg in messages[:-1]:  # Process complete messages
                print(f"[DEBUG] Server received raw message: {msg}")  # ✅ Debugging received message
                try:
                    json_msg = json.loads(msg)
                    print(f"[DEBUG] Parsed JSON message: {json_msg}")  # ✅ Show parsed JSON
                    return json_msg  # ✅ If it's JSON, return it as a dictionary
                except json.JSONDecodeError:
                    print(f"[DEBUG] Received raw text: {msg.strip()}")  # ✅ Show raw text
                    return msg.strip()  # ✅ Otherwise, return as a plain string

            buffer = messages[-1]  # Keep partial message in buffer
        except ConnectionAbortedError:
            print("[ERROR] Connection was closed by the client.")
            return None
        except ConnectionResetError:
            print("[ERROR] Connection reset by peer.")
            return None
def send_to_server(client_socket, message):
    """Sends a raw message (text or JSON) to the server."""
    try:
        if isinstance(message, dict):  # ✅ If it's JSON, send it properly
            json_data = json.dumps(message) + "\n"
            client_socket.sendall(json_data.encode('utf-8'))
            print(f"[DEBUG] Sent JSON to server: {json_data}")  # ✅ Debug sent JSON
        else:  # ✅ Otherwise, send as raw text
            message = message.strip() + "\n"
            client_socket.sendall(message.encode('utf-8'))
            print(f"[DEBUG] Sent raw message to server: {message}")  # ✅ Debug sent raw text
    except Exception as e:
        print(f"[ERROR] Failed to send to server: {e}")

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
    global clients
    if not message:
        print("[ERROR] send_to_all() was called without a message!")
        return
    print(f"[DEBUG] send_to_all() called with: {message}")
    for client_socket, _ in clients:
        try:
            send_json(client_socket, message)  # ✅ Uses send_json() for consistency
        except Exception as e:
            print(f"[ERROR] Failed to send to client {client_socket}: {e}")
