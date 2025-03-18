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

    if game is None:  # ✅ Prevents overwriting an existing game
        game = Game(*players)
        print("[DEBUG] Game initialized.")
    else:
        print("[WARNING] Game already exists. Not reinitializing.")

    send_to_all({"command": "start"})  # ✅ Uses correct function to notify all clients
    if len(clients) > 0:
        host_socket, _ = clients[0]  # ✅ The first client is always the host
        send_to_client(host_socket, {
            "command": "you_are_host",
            "message": "You are the host. Please start the game."
        })  # ✅ Sends private message to the host
        print(f"[DEBUG] Sent host notification to Player 1 ({host_socket})")
    for client_socket, player in clients:
        print(f"[DEBUG] Starting client handler for {player.name}")
        threading.Thread(target=handle_client, args=(client_socket, player)).start()

    print("[EXIT] start_game()")


def handle_client(client_socket, player):
    """Handles communication with a single client after the game starts."""
    global game
    print(f"[ENTER] handle_client({player.name})")

    try:
        while True:
            # Send updated game state
            game_state = {
                "command": "game_state",
                "turn": game.players[game.turn].name,
                "your_cards": [str(card) for card in player.get_visible_cards()],
                "actions": game.get_available_actions(),
                "discard_pile": [str(card) for card in game.discard_pile]
            }
            print(f"[DEBUG] Sending game state to {player.name}: {game_state}")
            send_json(client_socket, game_state)

            # Receive the player's action
            action_data = receive_json(client_socket)
            if not action_data:
                print(f"[DEBUG] Player {player.name} disconnected. Closing connection.")
                break  # ✅ Explicitly break loop if player disconnects

            if action_data.get("command") == "action":
                action = action_data["data"]
                print(f"[DEBUG] {player.name} chose action: {action}")

                if game.players[game.turn] == player:
                    send_to_client(client_socket, {"command": "your_turn"})  # ✅ Notifies the player that it's their turn
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




