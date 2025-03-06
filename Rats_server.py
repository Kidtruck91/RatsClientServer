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
    print(f"DEBUG: handle_client started for {player.name}")
    try:
        while True:
            # Send the game state to the client
            print(f"DEBUG: Sending game state to {player.name}")
            print(f"DEBUG: Game turn = {game.players[game.turn].name}")
            print(f"DEBUG: Player hands = {[p.get_visible_cards() for p in game.players]}")
            print(f"DEBUG: Discard pile = {game.discard_pile}")

            game_state = (game, player.name)
            print(f"DEBUG: Sending actual game state to {player.name} -> {type(game_state)}")
            print(f"DEBUG: Game object type: {type(game)}")
            print(f"DEBUG: Player name sent: {player.name}")
            client_socket.sendall(pickle.dumps(game_state))



            # Receive the player's action
            data = client_socket.recv(4096)
            if not data:
                break  # Exit loop if the client disconnects

            action = pickle.loads(data)
            print(f"{player.name} chose action: {action}")

            # Perform the action if it's the player's turn
            if game.players[game.turn] == player:
                game.perform_action(player, action,client_socket, send_to_all)

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

            if response.get("start_game") and player.name == "Player 1":
                print("DEBUG: Host started the game!")
                send_to_all({"command": "start"})
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
    print(f"DEBUG: Players in the game: {[p.name for _, p in clients]}")
    print(f"DEBUG: Current Turn: {game.players[game.turn].name}")


    # Send start signal to all clients
    send_to_all({"command": "start"})

    # Start game communication threads
    for client_socket, player in clients:
        print(f"DEBUG: Starting thread for {player.name}")
        threading.Thread(target=handle_client, args=(client_socket, player)).start()

def start_server():
    """Starts the server and waits for players to connect."""
    
    global game
    update_noip()
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

        # ✅ Immediately send updated player list to ALL clients (including the host)
        updated_players = {"command": "waiting", "players": [p.name for _, p in clients]}
        send_to_all(updated_players)
        print(f"DEBUG: Sent updated player list to all clients: {updated_players}")

        # ✅ Assign the first player as the host
        if len(clients) == 1:
            print(f"👑 Player {player_id} is the host!")
            send_to_client(client_socket, {"command": "host_control", "players": [p.name for _, p in clients]})
            threading.Thread(target=handle_host, args=(client_socket, new_player)).start()

        if len(clients) >= 2:
            print("⏳ Waiting for host to start the game...")


if __name__ == "__main__":
    start_server()
