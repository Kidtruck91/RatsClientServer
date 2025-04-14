import threading
import socket
import requests

from network_utils import connected_clients,connected_players,client_socket_lookup, SERVER_HOST,SERVER_PORT, send_json, receive_json,send_to_all,send_to_client,send_to_player
from game_logic import Game, Player,Deck
NOIP_HOSTNAME = "ratsmpserver.ddns.net"
NOIP_USERNAME = "2by66j9"
NOIP_UPDATE_KEY = "Evhv3AVaYpLh"

game = None



# Cards dealt to players first
cards = [
    (7, 0), (8, 1), (9, 2),  # Player 1's hand
    (12, 0), (4, 1), (5, 2),  # Player 2's hand
    (12, 2),                 # 👈 Player 1's first draw — Queen of Hearts
    (6, 3), (11, 0), (2, 1), # More filler cards if needed
]

# Create a fixed deck
rigged_deck = Deck.fixed_deck(cards)





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
    global game, connected_players, connected_clients
    print("[ENTER] start_game()")

    # Initialize game using known-good list of Player objects
    
    #game = Game(connected_players)
    game = Game(connected_players, draw_pile=rigged_deck.cards)
    print("[DEBUG] Game initialized with players:", [p.name for p in connected_players])

    # Notify all clients
    send_to_all({"command": "start", "message": "The game is starting!"})
    print("[DEBUG] Sent game start notification to all players.")

    # Launch a thread for each client/player pair
    for client_socket, player in connected_clients:
        print(f"[DEBUG] Starting client handler for {player.name}")
        threading.Thread(target=handle_client, args=(client_socket, player), daemon=False).start()

    print("[EXIT] start_game()")


def accept_new_players(server, send_to_all, send_json):
    """Continuously accepts new player connections while waiting for the host to start the game."""
    from network_utils import connected_players, connected_clients, client_socket_lookup
    print("[DEBUG] accept_new_players() started!")

    while len(connected_players) < 4:
        try:
            client_socket, addr = server.accept()
            print(f"[DEBUG] New connection from {addr}")

            player_id = len(connected_players) + 1
            new_player = Player(f"Player {player_id}")
            connected_players.append(new_player)
            connected_clients.append((client_socket, new_player))

            client_socket_lookup[new_player.name] = client_socket

            send_to_all({"command": "waiting", "players": [p.name for p in connected_players]})
            print(f"[DEBUG] Current connected players: {[p.name for p in connected_players]}")

            if len(connected_players) == 1:
                print(f"[DEBUG] Player {player_id} is the host.")
                send_json(client_socket, {"command": "host_control", "players": [p.name for p in connected_players]})

        except Exception as e:
            print(f"[ERROR] Failed to accept new connection: {e}")

def end_turn_and_update_all():
    game.advance_turn()
    next_player = game.players[game.turn]
    send_to_all({
        "command": "message",
        "data": f"Turn has advanced to: {next_player.name}"
    })
    for p in game.players:
        client = client_socket_lookup[p.name]
        game_state = {
            "command": "game_state",
            "turn": game.players[game.turn].name,
            "player_name": p.name,
            "your_cards": [str(card) for card in p.get_visible_cards()],
            "actions": game.get_available_actions(),
            "discard_pile": [str(card) for card in game.discard_pile]
        }
        send_json(client, game_state)

def handle_client(client_socket, player):
    """Handles communication with a single client after the game starts."""
    global game
    print(f"[ENTER] handle_client({player.name})")

    try:
        while True:
            # Send updated game state
            if player.name not in game.pending_prompts:
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
            else:
                print(f"[DEBUG] Skipping game_state for {player.name}, pending prompt exists.")
            # Receive next action/response
            action_data = receive_json(client_socket)
            print(f"[DEBUG] Received from {player.name}: {action_data}")

            if not action_data:
                print(f"[DEBUG] Player {player.name} disconnected. Closing connection.")
                break

            match action_data.get("command"):
                case "action":
                    action_case(player, client_socket, action_data)
                    continue  

                case "response":
                    response_case(player, client_socket, action_data)
                    continue
  

                case other:
                    print(f"[WARNING] Unknown command from {player.name}: {other}")

    except (ConnectionResetError, EOFError):
        print(f"[DEBUG] {player.name} disconnected unexpectedly.")

    except Exception as e:
        print(f"[ERROR] Issue handling client {player.name}: {e}")

    finally:
        print(f"[EXIT] handle_client({player.name})")
        client_socket.close()

def response_case(player, client_socket, action_data):
    """Handles a single response to a server prompt."""
    global game
    print("[DEBUG] Starting response case")
    
    response = action_data["data"]
    prompt_type = action_data.get("type")
    print(f"[DEBUG] {player.name} responded with: {response}")
    print(f"[DEBUG] response= {response}, prompt type = {prompt_type}")
    if game.players[game.turn] != player:
        print(f"[DEBUG] {player.name} attempted to respond out of turn.")
        return

    match prompt_type:

        # --- Card Replacement (Draw/Discard)
        case "card_replacement":
            
            prompt_info = game.pending_prompts.pop(player.name, {})
            drawn_card = prompt_info.get("card")
            if not drawn_card:
                print(f"[ERROR] No drawn card found in prompt_info: {prompt_info}")
                return
            try:
                replace_index = int(response)
            except ValueError:
                send_json(client_socket, {
                    "command": "tell",
                    "message": "Invalid input. Enter 0, 1, 2, or -1."
                })
                game.pending_prompts[player.name] = prompt_info
                send_json(client_socket, {
                    "command": "prompt",
                    "type": "card_replacement",
                    "data": "Choose which card to replace (0, 1, 2) or -1 to discard:",
                    "card_drawn": str(drawn_card)
                })
                return

            game.handle_card_replacement(player, replace_index, drawn_card, client_socket)
            if player.name not in game.pending_prompts:
                end_turn_and_update_all()
            return

        # --- Jack Logic
        case "jack_peek_choice":
            if response == "1":
                game.peek_self(player, client_socket)
            elif response == "2":
                game.peek_opponent(player, client_socket)
            else:
                send_json(client_socket, {
                    "command": "tell",
                    "message": "Invalid choice. Enter 1 (self) or 2 (opponent)."
                })
            return

        case "peek_self_index":
            try:
                index = int(response)
                player.revealed_cards[index] = True
                send_to_player(player, {
                    "command": "tell",
                    "message": f"You peeked at: {Deck.card_to_string(player.cards[index])}"
                })
            except Exception:
                send_to_player(player, {
                    "command": "tell",
                    "message": "Invalid index. Enter 0, 1, or 2."
                })
            end_turn_and_update_all()
            return

        case "peek_opponent_select":
            try:
                prompt_info = game.pending_prompts[player.name]
                opponents = prompt_info["opponents"]
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
            except Exception:
                send_to_player(player, {
                    "command": "tell",
                    "message": "Invalid opponent. Try again."
                })
            return

        case "peek_opponent_card_index":
            try:
                opponent = game.pending_prompts[player.name]["opponent"]
                peek_index = int(response)
                card = opponent.cards[peek_index]
                player.add_known_opponent_card(opponent.name, peek_index, card)
                send_to_player(player, {
                    "command": "tell",
                    "message": f"You peeked at {opponent.name}'s card: {Deck.card_to_string(card)}"
                })
            except Exception:
                send_to_player(player, {
                    "command": "tell",
                    "message": "Invalid index. Try 0, 1, or 2."
                })
            end_turn_and_update_all()
            return

        # --- Queen Logic
        case "queen_pick_first_player":
            try:
                index = int(response)
                opponents = game.pending_prompts[player.name]["opponents"]
                target1 = opponents[index]
                game.pending_prompts.pop(player.name)
                game.ask_queen_first_card(player, target1, client_socket)
            except Exception:
                send_json(client_socket, {
                    "command": "tell",
                    "message": "Invalid selection. Try again."
                })
            return

        case "queen_pick_first_card":
            try:
                card_index = int(response)
                prompt_info = game.pending_prompts.pop(player.name)
                target1 = prompt_info["target1"]
                game.ask_queen_second_player(player, target1, card_index, client_socket)
            except Exception:
                send_json(client_socket, {
                    "command": "tell",
                    "message": "Invalid card selection. Try again."
                })
            return

        case "queen_pick_second_player":
            try:
                index = int(response)
                prompt_info = game.pending_prompts.pop(player.name)
                target1 = prompt_info["target1"]
                index1 = prompt_info["index1"]
                target2 = prompt_info["opponents"][index]
                game.ask_queen_second_card(player, target1, index1, target2, client_socket)
            except Exception as e:
                print(f"[ERROR] Queen second player error: {e}")
                send_json(client_socket, {
                    "command": "tell",
                    "message": "Invalid player. Try again."
                })
            return

        case "queen_pick_second_card":
            try:
                index2 = int(response)
                prompt_info = game.pending_prompts.pop(player.name)
                target1 = prompt_info["target1"]
                index1 = prompt_info["index1"]
                target2 = prompt_info["target2"]

                if target1 == target2 and index1 == index2:
                    send_json(client_socket, {
                        "command": "tell",
                        "message": "Cannot swap a card with itself."
                    })
                    game.pending_prompts[player.name] = prompt_info
                    send_json(client_socket, {
                        "command": "prompt",
                        "type": "queen_pick_second_card",
                        "data": "Choose a different card to complete the swap."
                    })
                    return

                # Perform swap
                card1 = target1.cards[index1]
                card2 = target2.cards[index2]
                target1.cards[index1], target2.cards[index2] = card2, card1
                print(f"[DEBUG] {player.name} swapped {target1.name}[{index1}] with {target2.name}[{index2}]")

                # Knowledge transfer
                if player.name in target1.card_known_by[index1]:
                    target2.reveal_card_to(index2, player.name)
                else:
                    target2.revealed_cards[index2] = False
                if player.name in target2.card_known_by[index2]:
                    target1.reveal_card_to(index1, player.name)
                else:
                    target1.revealed_cards[index1] = False

                send_to_player(player, {
                    "command": "tell",
                    "message": f"You swapped {target1.name}'s card with {target2.name}'s card."
                })
            except Exception as e:
                print(f"[ERROR] Queen swap error: {e}")
                send_json(client_socket, {
                    "command": "tell",
                    "message": "Invalid selection. Try again."
                })
            end_turn_and_update_all()
            return

        # --- Fallback
        case _:
            print(f"[DEBUG] Unknown prompt type: {prompt_type}")
    print("[DEBUG] Ending response case")

def action_case(player, client_socket, action_data):
    global game

    action = action_data["data"]
    print(f"[DEBUG] {player.name} chose action: {action}")

    if game.players[game.turn] == player:
        game.perform_action(player, action, client_socket, send_to_all)

        if game.game_over:
            print("[DEBUG] Game over! Notifying clients.")
            send_json(client_socket, {"command": "game_over"})
    else:
        print(f"[DEBUG] {player.name} attempted an action out of turn.")





