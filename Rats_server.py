import socket
import pickle
import threading
from game_logic import Game, Player

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5555
clients = []

def handle_client(conn, player_id, game):
    """Handles communication with a single client."""
    while True:
        try:
            conn.sendall(pickle.dumps(game))
            action = pickle.loads(conn.recv(4096))
            current_player = game.players[game.turn]
            if current_player.name == f"Player {player_id}":
                game.perform_action(current_player, action)
                game.advance_turn()
        except (ConnectionResetError, EOFError):
            print(f"Player {player_id} disconnected.")
            break
    conn.close()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((SERVER_HOST, SERVER_PORT))
server.listen(4)
print("Waiting for players...")

game = Game(*[Player(f"Player {i+1}") for i in range(4)])

for i in range(4):
    conn, addr = server.accept()
    print(f"Player {i+1} connected from {addr}")
    clients.append(conn)
    threading.Thread(target=handle_client, args=(conn, i+1, game)).start()
