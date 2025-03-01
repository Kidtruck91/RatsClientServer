import socket
import pickle
import threading
import requests
from game_logic import Game, Player
# No-IP Credentials
NOIP_HOSTNAME = "ratsmpserver.ddns.net"  # Replace with your No-IP hostname
NOIP_USERNAME = "2by66j9"
NOIP_UPDATE_KEY = "Evhv3AVaYpLh"

def update_noip():
    """Updates No-IP with the server's current public IP."""
    url = f"https://dynupdate.no-ip.com/nic/update?hostname={NOIP_HOSTNAME}"
    response = requests.get(url, auth=(NOIP_USERNAME, NOIP_UPDATE_KEY))

    if "good" in response.text or "nochg" in response.text:
        print(f"✅ No-IP Updated Successfully: {response.text}")
    else:
        print(f"❌ No-IP Update Failed: {response.status_code} - {response.text}")

def get_public_ip():
    """Fetches the server's current public IP address."""
    return requests.get("https://ifconfig.me/ip").text.strip()

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5555

clients = []  # List of (socket, player_name) tuples
game = None   # Global game instance

def send_to_client(client_socket, message):
    """Sends a pickled message to a client."""
    try:
        client_socket.sendall(pickle.dumps(message))
    except Exception as e:
        print(f"Error sending message to client: {e}")

def send_to_all(message):
    """Sends a pickled message to all clients."""
    print(f"DEBUG: Sending to all clients: {message}")  
    for client_socket, _ in clients:
        try:
            client_socket.sendall(pickle.dumps(message))
        except Exception as e:
            print(f"Error sending to client: {e}")

def handle_client(client_socket, player_name):
    """Handles communication with a single client after the game starts."""
    global game

    try:
        while True:
            game_state = pickle.dumps((game, player_name))
            client_socket.sendall(game_state)

            data = client_socket.recv(4096)
            if not data:
                break  

            action = pickle.loads(data)
            print(f"{player_name} chose action: {action}")

            if game.players[game.turn].name == player_name:
                game.perform_action(game.players[game.turn], action, client_socket, send_to_all)
                send_to_all((game, player_name))

                if game.game_over:
                    break

    except (ConnectionResetError, EOFError):
        print(f"{player_name} disconnected unexpectedly.")
    
    finally:
        client_socket.close()

def handle_host(client_socket):
    """Handles the host before the game starts."""
    try:
        while True:
            send_to_client(client_socket, {"command": "host_control", "players": [p[1] for p in clients]})

            response = pickle.loads(client_socket.recv(4096))
            print(f"DEBUG: Host response received: {response}")

            if response.get("start_game"):
                print("🎮 Host started the game!")
                send_to_all({"command": "start"})  
                start_game()  
                return  

    except Exception as e:
        print(f"❌ Host disconnected before starting: {e}")

def start_game():
    """Initializes and starts the game with connected players."""
    global game
    if game:
        print("⚠️ Game has already started! Ignoring extra start command.")
        return  

    game = Game(*[Player(p[1]) for p in clients])  
    print("🎮 Game is starting...")

    send_to_all({"command": "start"})  

    for client_socket, player_name in clients:
        threading.Thread(target=handle_client, args=(client_socket, player_name)).start()

def start_server():
    """Starts the game server, updates No-IP, and assigns the first player as the host."""
    global game, clients

    public_ip = get_public_ip()
    print(f"🌍 Server Public IP: {public_ip}")
    update_noip()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 5555))
    server.listen(4)

    print(f"🚀 Server started at {public_ip}:5555 - Clients should connect to {NOIP_HOSTNAME}")

    players_connected = 0

    while players_connected < 4:  
        client_socket, addr = server.accept()
        print(f"✅ Player connected from {addr}")
        players_connected += 1

        player_name = f"Player {players_connected}"
        clients.append((client_socket, player_name))

        send_to_all({"command": "waiting", "players": [p[1] for p in clients]})

        if players_connected == 1:
            print(f"👑 {player_name} is the host!")
            send_to_client(client_socket, {"command": "host_control", "players": [p[1] for p in clients]})
            threading.Thread(target=handle_host, args=(client_socket,)).start()

if __name__ == "__main__":
    start_server()