import socket
import threading
import json
from game_logic import Game, Player
from server_utils import start_game
from network_utils import clients,players, SERVER_HOST,SERVER_PORT, send_json, receive_json,send_to_all,send_to_client
def start_server():
    """Starts the server and waits for players to connect."""
    global players, clients
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(4)

    print("\n🚀 **Rats! Multiplayer Server is Running!** 🚀")
    print(f"🌐 Port: {SERVER_PORT}")
    print("📢 Waiting for players to connect...\n")

    try:
        while len(players) < 4:  # Allow up to 4 players
            try:
                client_socket, addr = server.accept()
                print(f"[DEBUG] New connection from {addr}")

                player_id = len(players) + 1
                new_player = Player(f"Player {player_id}")
                players.append(new_player)
                clients.append((client_socket, new_player))

                # Notify all players of the updated list
                send_to_all({"command": "waiting", "players": [p.name for p in players]})

                print(f"[DEBUG] Current connected players: {[p.name for p in players]}")

                if len(players) == 1:
                    print(f"[DEBUG] Player {player_id} is the host.")
                    send_json(client_socket, {"command": "host_control", "players": [p.name for p in players]})

                if len(players) >= 2:
                    print("[DEBUG] Waiting for the host to start the game...")

            except Exception as e:
                print(f"[ERROR] Failed to accept new connection: {e}")

        # Wait for host input to start game
        while True:
            if len(clients) > 0:  # ✅ Ensure clients exist before accessing
                try:
                    print("[DEBUG] Waiting for host to start the game...")
                    game_start_msg = receive_json(clients[0][0])  # Host input

                    print(f"[DEBUG] Received message: {game_start_msg}")  # ✅ Debugging received data

                    if game_start_msg and game_start_msg.get("command") == "start_game":
                        print("[DEBUG] Received 'start_game' command from host. Starting game...")
                        start_game()
                        break
                except Exception as e:
                    print(f"[ERROR] Failed to receive start command: {e}")

    except KeyboardInterrupt:
        print("[INFO] Server shutting down...")
        server.close()


if __name__ == "__main__":
    try:
        start_server()
    except Exception as e:
        print(f"[ERROR] Server crashed: {e}")
