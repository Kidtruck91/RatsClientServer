import threading
import socket
import requests

from network_utils import clients,players,client_socket_lookup, SERVER_HOST,SERVER_PORT, send_json, receive_json,send_to_all,send_to_client,send_to_player
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

            # ✅ Add this line to track the player's socket by name
            client_socket_lookup[new_player.name] = client_socket

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
            # Send updated game state
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

            # Receive next action/response
            action_data = receive_json(client_socket)
            print(f"[DEBUG] Received from {player.name}: {action_data}")

            if not action_data:
                print(f"[DEBUG] Player {player.name} disconnected. Closing connection.")
                break

            match action_data.get("command"):
                case "action":
                    action = action_data["data"]
                    print(f"[DEBUG] {player.name} chose action: {action}")

                    if game.players[game.turn] == player:
                        game.perform_action(player, action, client_socket, send_to_all)

                        if game.game_over:
                            print("[DEBUG] Game over! Notifying clients.")
                            send_json(client_socket, {"command": "game_over"})
                            break
                    else:
                        print(f"[DEBUG] {player.name} attempted an action out of turn.")

                case "response":
                    response = action_data["data"]
                    prompt_type = action_data.get("type")
                    print(f"[DEBUG] {player.name} responded with: {response}")

                    if game.players[game.turn] != player:
                        print(f"[DEBUG] {player.name} attempted to respond out of turn.")
                        continue

                    # --- Handle card replacement after drawing ---
                    if prompt_type == "card_replacement" and player.name in game.pending_prompts:
                        prompt_info = game.pending_prompts.pop(player.name)
                        drawn_card = prompt_info["card"]

                        try:
                            replace_index = int(response)
                        except ValueError:
                            print(f"[ERROR] Invalid card index: {response}")
                            send_json(client_socket, {
                                "command": "tell",
                                "message": "Invalid input. Please enter 0, 1, 2, or -1."
                            })
                            game.pending_prompts[player.name] = prompt_info
                            send_json(client_socket, {
                                "command": "prompt",
                                "type": "card_replacement",
                                "data": "Choose which card to replace (0, 1, 2) or -1 to discard:",
                                "card_drawn": str(drawn_card)
                            })
                            continue

                        game.handle_card_replacement(player, replace_index, drawn_card)

                        # Turn ends after replacement
                        game.advance_turn()
                        next_player = game.players[game.turn]
                        send_to_all({
                            "command": "message",
                            "data": f"Turn has advanced to: {next_player.name}"
                        })
                        send_to_client(client_socket_lookup[next_player.name], {
                            "command": "your_turn",
                            "message": "It's your turn!"
                        })

                    # --- Handle Jack: choose peek type ---
                    elif prompt_type == "jack_peek_choice":
                        if response == "1":
                            game.peek_self(player, client_socket)
                        elif response == "2":
                            game.peek_opponent(player, client_socket)
                        else:
                            send_json(client_socket, {
                                "command": "tell",
                                "message": "Invalid choice. Enter 1 (self) or 2 (opponent)."
                            })

                    # --- Peek self ---
                    elif prompt_type == "peek_self_index":
                        try:
                            index = int(response)
                            player.revealed_cards[index] = True
                            send_to_player(player, {
                                "command": "tell",
                                "message": f"You peeked at: {Deck.card_to_string(player.cards[index])}"
                            })

                            game.advance_turn()
                            next_player = game.players[game.turn]
                            send_to_all({
                                "command": "message",
                                "data": f"Turn has advanced to: {next_player.name}"
                            })
                            send_to_client(client_socket_lookup[next_player.name], {
                                "command": "your_turn",
                                "message": "It's your turn!"
                            })
                        except Exception as e:
                            print(f"[ERROR] Invalid peek_self_index: {response}")
                            send_to_player(player, {
                                "command": "tell",
                                "message": "Invalid index. Please enter 0, 1, or 2."
                            })

                    # --- Peek opponent: choose opponent ---
                    elif prompt_type == "peek_opponent_select":
                        prompt_info = game.pending_prompts[player.name]
                        opponents = prompt_info["opponents"]
                        try:
                            opp_index = int(response)
                            opponent = opponents[opp_index]
                            game.pending_prompts[player.name] = {
                                "type": "peek_opponent_card_index",
                                "opponent": opponent
                            }
                            send_to_player(player, {
                                "command": "prompt",
                                "type": "peek_opponent_card_index",
                                "data": f"Choose a card to peek at from {opponent.name} (0, 1, 2):"
                            })
                        except Exception as e:
                            print(f"[ERROR] Invalid opponent selection: {response}")
                            send_to_player(player, {
                                "command": "tell",
                                "message": "Invalid opponent. Try again."
                            })

                    # --- Peek opponent: choose card index ---
                    elif prompt_type == "peek_opponent_card_index":
                        opponent = game.pending_prompts[player.name]["opponent"]
                        try:
                            peek_index = int(response)
                            card = opponent.cards[peek_index]
                            player.add_known_opponent_card(opponent.name, peek_index, card)
                            send_to_player(player, {
                                "command": "tell",
                                "message": f"You peeked at {opponent.name}'s card: {Deck.card_to_string(card)}"
                            })

                            game.advance_turn()
                            next_player = game.players[game.turn]
                            send_to_all({
                                "command": "message",
                                "data": f"Turn has advanced to: {next_player.name}"
                            })
                            send_to_client(client_socket_lookup[next_player.name], {
                                "command": "your_turn",
                                "message": "It's your turn!"
                            })
                        except Exception as e:
                            print(f"[ERROR] Invalid card index: {response}")
                            send_to_player(player, {
                                "command": "tell",
                                "message": "Invalid index. Try 0, 1, or 2."
                            })
                    else:
                        print(f"[DEBUG] No prompt to match response type: {prompt_type}")

                case other:
                    print(f"[WARNING] Unknown command from {player.name}: {other}")

    except (ConnectionResetError, EOFError):
        print(f"[DEBUG] {player.name} disconnected unexpectedly.")

    except Exception as e:
        print(f"[ERROR] Issue handling client {player.name}: {e}")

    finally:
        print(f"[EXIT] handle_client({player.name})")
        client_socket.close()







