import socket
import pickle
import threading
from game_logic import Game, Player

# Get the server's local IP address
def get_local_ip():
    """Finds the local IP address of the device running the server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"  # Fallback to localhost
    finally:
        s.close()
    return local_ip

SERVER_HOST = get_local_ip()  # Get current machine's IP
SERVER_PORT = 5555            # Port to listen on

clients = []
game = None
player_count = 0

def start_server():
    """Starts the server and waits for players to connect."""
    global game, player_count

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(4)  # Allow up to 4 players

    # **Print connection info for clients**
    print(f"🖥️  Rats! Multiplayer Server is running on:")
    print(f"   📡 Local IP: {SERVER_HOST}")
    print(f"   🌐 Port: {SERVER_PORT}")
    print("\nClients should manually enter this IP and port to connect.")

    players = []
    while len(players) < 4:
        client_socket, addr = server.accept()
        player_id = len(players) + 1
        print(f"Player {player_id} connected from {addr}")

        new_player = Player(f"Player {player_id}", is_human=True)
        players.append(new_player)

        clients.append((client_socket, player_id))

        if len(players) >= 2:
            break

    # Initialize the game with connected players
    game = Game(*players)
    print("🎮 Game is starting...")

    # Start client threads
    for client_socket, player_id in clients:
        client_thread = threading.Thread(target=handle_client, args=(client_socket, player_id))
        client_thread.start()


if __name__ == "__main__":
    start_server()
