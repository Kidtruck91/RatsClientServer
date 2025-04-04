import socket
import threading
import json
import time
from game_logic import Game, Player
from server_utils import start_game, accept_new_players
from network_utils import connected_clients, connected_players, SERVER_HOST, SERVER_PORT, receive_message, send_json, receive_json, send_to_all, send_to_client

def start_server():
    """Starts the server and waits for players to connect."""
    global connected_players, connected_clients
    print("[DEBUG] Entering start_server()")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(4)

    print("\n🚀 **Rats! Multiplayer Server is Running!** 🚀")
    print(f"🌐 Port: {SERVER_PORT}")
    print("📢 Waiting for players to connect...\n")

    try:
        # ✅ Fix: Pass `send_json` when calling `accept_new_players`
        print("[DEBUG] Starting accept_new_players thread...")
        threading.Thread(target=accept_new_players, args=(server, send_to_all, send_json), daemon=True).start()

        # ✅ Ensure at least 2 players before waiting for start
        while len(connected_players) < 2:
            print(f"[DEBUG] Waiting for players to join... (Current: {len(connected_players)})")
            time.sleep(1)  # ✅ Prevents infinite loop from blocking execution

        print("[DEBUG] Finished player connection loop, waiting for host input...")

        # ✅ Wait for host input to start the game
        while True:
            if len(connected_clients) > 0:  # ✅ Ensure clients exist before accessing
                try:
                    print("[DEBUG] Waiting for host to start the game...")
                    game_start_msg = receive_message(connected_clients[0][0])  # ✅ Host input

                    print(f"[DEBUG] Received message from host: {game_start_msg}")  # ✅ Debugging received data

                    if isinstance(game_start_msg, dict) and game_start_msg.get("command") == "start_game":
                        print("[DEBUG] Received 'start_game' command from host. Starting game...")
                        start_game()
                        break
                    elif isinstance(game_start_msg, str) and game_start_msg.strip().lower() == "start_game":
                        print("[DEBUG] Received 'start_game' as raw text. Starting game...")
                        start_game()
                        break

                except Exception as e:
                    print(f"[ERROR] Failed to receive start command: {e}")

    except KeyboardInterrupt:
        print("[INFO] Server shutting down...")
        server.close()

if __name__ == "__main__":
    print("[DEBUG] Running Rats server...")  # ✅ Ensure this appears in logs
    try:
        start_server()
    except Exception as e:
        print(f"[ERROR] Server crashed: {e}")
