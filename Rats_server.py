import socket
import pickle
import threading
from game_logic import Game, Player

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

SERVER_HOST = get_local_ip()  # Automatically detects and sets the local IP
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
    """Sends a pickled message to all clients."""
    for client_socket, _ in clients:
        send_to_client(client_socket, message)

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
                game.perform_action(player, action)

                # Check if the game is over
                if game.game_over:
                    break

    except (ConnectionResetError, EOFError):
        print(f"{player.name} disconnected unexpectedly.")
    
    finally:
        client_socket.close()

def handle_host(client_socket):
    """Handles the host before the game starts."""
    try:
        while True:
            # ✅ Send player list update to host
            send_to_client(client_socket, {"command": "host_control", "players": [p.name for _, p in clients]})

            response = pickle.loads(client_socket.recv(4096))
            print(f"DEBUG: Host response received: {response}")

            if response.get("start_game"):
                print("DEBUG: Host started the game!")
                start_game()
                break  # ✅ Exit loop after starting the game

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
    """Starts the server and waits for players to connect."""
    global game

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allows multiple connections on same machine
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(4)

    print("\n🚀 **Rats! Multiplayer Server is Running!** 🚀")
    print(f"🎮 Host IP Address: {SERVER_HOST}")  # ✅ Displays local IP
    print(f"🌐 Port: {SERVER_PORT}")
    print("📢 Clients should enter this IP in `Rats_Client.py` to connect!\n")

    print("Waiting for players to connect...")

    while len(clients) < 4:  # Allow up to 4 players
        client_socket, addr = server.accept()
        player_id = len(clients) + 1
        print(f"✅ Player {player_id} connected from {addr}")

        new_player = Player(f"Player {player_id}", is_human=True)
        clients.append((client_socket, new_player))
        send_to_all({"command": "waiting", "players": [p.name for _, p in clients]})
        # ✅ If the first player is connecting, they are the host
        if len(clients) == 1:
            print(f"👑 Player {player_id} is the host!")
            send_to_client(client_socket, {"command": "host_control", "players": [p.name for _, p in clients]})
            threading.Thread(target=handle_host, args=(client_socket,)).start()

        # ✅ Update all clients about player changes
        send_to_all({"command": "waiting", "players": [p.name for _, p in clients]})

        if len(clients) >= 2:
            print("⏳ Waiting for host to start the game...")


if __name__ == "__main__":
    start_server()
