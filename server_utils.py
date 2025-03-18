import threading
import socket
import requests

from network_utils import clients,players, SERVER_HOST,SERVER_PORT, send_json, receive_json,send_to_all,send_to_client
from game_logic import Game, Player
NOIP_HOSTNAME = "ratsmpserver.ddns.net"
NOIP_USERNAME = "2by66j9"
NOIP_UPDATE_KEY = "Evhv3AVaYpLh"

game = None



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

def start_game():
    """Initializes and starts the game."""
    global game, players, clients
    print("[ENTER] start_game()")

    # ✅ Debugging what `players` actually contains
    print(f"[DEBUG] Players data type: {type(players)}")
    print(f"[DEBUG] Players value: {players}")

    if not isinstance(players, list):  # ✅ Prevents crash if `players` is incorrect
        print("[ERROR] `players` is not a list! Fixing it...")
        players = [players]  # ✅ Convert `players` into a list

    # ✅ Ensure that all items in players are Player objects
    if not all(isinstance(p, Player) for p in players):
        print("[ERROR] `players` contains non-Player objects! Fixing it...")
        players = [p for p in players if isinstance(p, Player)]

    # ✅ Check if Game expects a list or separate Player objects
    try:
        game = Game(players)  # ✅ Instead of `Game(*players)`, try passing the list directly
        print("[DEBUG] Game initialized.")
    except TypeError as e:
        print(f"[ERROR] Game initialization failed: {e}")
        print("[DEBUG] Retrying with unpacking...")
        game = Game(*players)  # ✅ Fallback if `Game(players)` fails

    # ✅ Notify all players that the game is starting
    send_to_all({"command": "start", "message": "The game is starting!"})
    print("[DEBUG] Sent game start notification to all players.")

    # ✅ Start client handlers AFTER notifying players
    for client_socket, player in clients:
        print(f"[DEBUG] Starting client handler for {player.name}")
        threading.Thread(target=handle_client, args=(client_socket, player)).start()

    print("[EXIT] start_game()")

def accept_new_players(server, players, clients, send_to_all, send_json):
    """Continuously accepts new player connections while waiting for the host to start the game."""
    print("[DEBUG] accept_new_players() started!")

    while len(players) < 4:  # Allow up to 4 players
        try:
            client_socket, addr = server.accept()
            print(f"[DEBUG] New connection from {addr}")

            player_id = len(players) + 1
            new_player = Player(f"Player {player_id}")
            players.append(new_player)
            clients.append((client_socket, new_player))

            send_to_all({"command": "waiting", "players": [p.name for p in players]})
            print(f"[DEBUG] Current connected players: {[p.name for p in players]}")

            # ✅ Assign the first player as the host
            if len(players) == 1:
                print(f"[DEBUG] Player {player_id} is the host.")
                send_json(client_socket, {"command": "host_control", "players": [p.name for p in players]})

        except Exception as e:
            print(f"[ERROR] Failed to accept new connection: {e}")


def handle_client(client_socket, player):
    """Handles communication with a single client after the game starts."""
    global game
    print(f"[ENTER] handle_client({player.name})")

    try:
        while True:
            # ✅ Debugging what game_state actually contains
            game_state = {
                "command": "game_state",
                "turn": game.players[game.turn].name,
                "player_name": player.name,
                "your_cards": [str(card) for card in player.get_visible_cards()],
                "actions": game.get_available_actions(),
                "discard_pile": [str(card) for card in game.discard_pile]
            }
            print(f"[DEBUG] Sending game state to {player.name}: {game_state}")

            send_json(client_socket, game_state)

            # ✅ Debug the data before receiving
            action_data = receive_json(client_socket)
            print(f"[DEBUG] Received action from {player.name}: {action_data}")

            if not action_data:
                print(f"[DEBUG] Player {player.name} disconnected. Closing connection.")
                break  # ✅ Exit loop if player disconnects

            if action_data.get("command") == "action":
                action = action_data["data"]
                print(f"[DEBUG] {player.name} chose action: {action}")

                if game.players[game.turn] == player:
                    send_to_client(client_socket, {"command": "your_turn"})  # ✅ Notifies the player it's their turn
                    game.perform_action(player, action, client_socket, send_to_all)

                    if game.game_over:
                        print("[DEBUG] Game over! Notifying clients.")
                        send_json(client_socket, {"command": "game_over"})
                        break
                else:
                    print(f"[DEBUG] {player.name} attempted an action out of turn.")

    except (ConnectionResetError, EOFError):
        print(f"[DEBUG] {player.name} disconnected unexpectedly.")

    except Exception as e:
        print(f"[ERROR] Issue handling client {player.name}: {e}")

    finally:
        print(f"[EXIT] handle_client({player.name})")
        client_socket.close()





