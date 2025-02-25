import socket
import pickle
import threading
from game_logic import Game, Player

SERVER_HOST = "192.168.1.7"  # SErver(my home pc) IP address
SERVER_PORT = 5555

clients = []  # List to track connected clients
game = None   # Global game instance
player_count = 0  # Tracks number of connected players


def handle_client(client_socket, player_id):
    """Handles communication with a connected client."""
    global game

    try:
        while True:
            # Send the current game state to the client
            game_state = pickle.dumps((game, player_id))
            client_socket.sendall(game_state)

            # Receive the player's action
            data = client_socket.recv(4096)
            if not data:
                break  # Exit loop if the client disconnects

            action = pickle.loads(data)
            print(f"Player {player_id} chose action: {action}")

            # Perform the action
            current_player = game.players[game.turn]
            if current_player.name == f"Player {player_id}":
                game.perform_action(current_player, action)

                # Check if the game is over
                if game.game_over:
                    break

        print(f"Player {player_id} has left the game.")

    except (ConnectionResetError, EOFError):
        print(f"Player {player_id} disconnected unexpectedly.")

    finally:
        client_socket.close()


def start_server():
    """Starts the server and waits for players to connect."""
    global game, player_count

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(4)  # Maximum 4 players

    print(f"Server started on {SERVER_HOST}:{SERVER_PORT}")
    print("Waiting for players to connect...")

    players = []
    while len(players) < 4:  # Wait for up to 4 players
        client_socket, addr = server.accept()
        player_id = len(players) + 1
        print(f"Player {player_id} connected from {addr}")

        new_player = Player(f"Player {player_id}", is_human=True)
        players.append(new_player)

        clients.append((client_socket, player_id))

        if len(players) >= 2:  # Start game with at least 2 players
            break

    # Initialize the game with connected players
    game = Game(*players)
    print("Game is starting...")

    # Start a new thread for each player
    for client_socket, player_id in clients:
        client_thread = threading.Thread(target=handle_client, args=(client_socket, player_id))
        client_thread.start()


if __name__ == "__main__":
    start_server()
