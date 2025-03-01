import socket
import pickle
import threading
import requests
from game_logic import Game, Player
# No-IP Credentials
NOIP_HOSTNAME = "ratsmpserver.ddns.net"  # Replace with your No-IP hostname
NOIP_USERNAME = "2by66j9"
NOIP_PASSWORD = "Evhv3AVaYpLh"

def update_noip():
    """Updates No-IP with the server's current public IP."""
    url = f"https://dynupdate.no-ip.com/nic/update?hostname={NOIP_HOSTNAME}"
    response = requests.get(url, auth=(NOIP_USERNAME, NOIP_PASSWORD))

    if response.status_code == 200:
        print(f"✅ No-IP Updated: {response.text}")
    else:
        print(f"❌ No-IP Update Failed: {response.status_code} - {response.text}")

def get_public_ip():
    """Fetches the server's current public IP address."""
    return requests.get("https://ifconfig.me/ip").text.strip()
def get_local_ip():
    """Finds the local IP address of the server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # Connects to a public server to determine local IP
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"  # Fallback to localhost
    finally:
        s.close()
    return local_ip

SERVER_HOST = "0.0.0.0"#get_local_ip()  # Automatically detects and sets the local IP
SERVER_PORT = 5555

clients = []  # List of (socket, player) tuples
game = None   # Global game instance

def send_to_client(client_socket, message):
    """Sends a pickled message to a client."""
    try:
        client_socket.sendall(pickle.dumps(message))
    except Exception as e:
        print(f"Error sending message to client: {e}")

def send_to_all(message):
    """Sends a pickled message to all clients and logs it."""
    print(f"DEBUG: Sending to all clients: {message}")  # ✅ Debugging log
    for client_socket, _ in clients:
        try:
            client_socket.sendall(pickle.dumps(message))
        except Exception as e:
            print(f"Error sending to client: {e}")


def handle_client(client_socket, player):
    """Handles communication with a single client after the game starts."""
    global game

    try:
        while True:
            # Send the game state to the client
            game_state = pickle.dumps((game, player.name))
            client_socket.sendall(game_state)

            # Receive the player's action
            data = client_socket.recv(4096)
            if not data:
                break  # Exit loop if the client disconnects

            action = pickle.loads(data)
            print(f"{player.name} chose action: {action}")

            # Perform the action if it's the player's turn
            if game.players[game.turn] == player:
                game.perform_action(player, action,client_socket, send_to_all)
                send_to_all((game, player.name))

                # Check if the game is over
                if game.game_over:
                    break

    except (ConnectionResetError, EOFError):
        print(f"{player.name} disconnected unexpectedly.")
    
    finally:
        client_socket.close()

def handle_host(client_socket, player):
    """Handles the host before the game starts, ensuring they receive player updates."""
    try:
        while True:
            # ✅ Send the current player list to the host
            updated_players = {"command": "waiting", "players": [p.name for _, p in clients]}
            send_to_client(client_socket, updated_players)
            print(f"DEBUG: Sent player list update to host: {updated_players}")

            response = pickle.loads(client_socket.recv(4096))
            print(f"DEBUG: Host response received: {response}")

            if response.get("start_game"):
                print("DEBUG: Host started the game!")
                start_game()

                # ✅ Transition the host to normal gameplay (ensures they get updates)
                handle_client(client_socket, player)
                return  # ✅ Exit `handle_host()` after game starts

    except Exception as e:
        print(f"Host disconnected before starting: {e}")

def start_game():
    """Initializes and starts the game with connected players."""
    global game
    if game:
        print("⚠️ Game has already started! Ignoring extra start command.")
        return  # ✅ Prevent multiple game starts
    game = Game(*[p for _, p in clients])  # Use connected players
    print("🎮 Game is starting...")

    # Send start signal to all clients
    send_to_all({"command": "start"})

    # Start game communication threads
    for client_socket, player in clients:
        threading.Thread(target=handle_client, args=(client_socket, player)).start()

def start_server():
    """Starts the game server and updates No-IP."""
    global game

    # ✅ Get public IP and update No-IP
    public_ip = get_public_ip()
    print(f"🌍 Server Public IP: {public_ip}")
    update_noip()

    # ✅ Start the server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 5555))  # Listen on all interfaces
    server.listen(4)

    print(f"🚀 Server started at {public_ip}:5555 - Clients should connect to {NOIP_HOSTNAME}")

    while len(clients) < 4:
        client_socket, addr = server.accept()
        print(f"✅ Player connected from {addr}")
        clients.append(client_socket)

def send_to_all(message):
    """Sends a pickled message to all connected clients."""
    print(f"DEBUG: Sending to all clients: {message}")  # ✅ Debugging log
    for client_socket, _ in clients:
        try:
            client_socket.sendall(pickle.dumps(message))
        except Exception as e:
            print(f"Error sending to client: {e}")


if __name__ == "__main__":
    start_server()
