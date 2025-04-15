import threading
import socket
import time
import json
import sys
import select
from network_utils import send_json, receive_json,send_to_server
from game_logic import Game, Player,Deck
SERVER_HOST = "ratsmpserver.ddns.net"  
SERVER_PORT = 5555

def handle_host_input(client):
    """Allows the host to start the game when ready, but only if there are at least 2 players."""
    print("[DEBUG_CLIENT_UTILS_handle_host_input] Entering handle_host_input")
    
    while True:
        print("Type 'start' to begin the game (minimum 2 players required).")
        
        #   Check the number of players before allowing "start"
        game_state = receive_json(client)
        if game_state.get("command") == "waiting":
            players = game_state.get("players", [])
            print(f"[DEBUG_CLIENT_UTILS_handle_host_input] Current players: {players}")

            if len(players) < 2:
                print("[ERROR_CLIENT_UTILS_] At least 2 players are required to start the game.")
                time.sleep(2)  #   Prevent spam, wait before checking again
                continue  #   Keep checking until enough players join

        command = input(">> ").strip().lower()
        if command == "start":
            send_to_server(client, {"command": "start_game"})
            print("[DEBUG_CLIENT_UTILS_] Sent start command to server.")
            break
        else:
            print("[ERROR_CLIENT_UTILS_] Invalid command. Type 'start' to begin the game.")
            continue



def parse_card_string(card_str):
    """Parses a string like '(11, 2)' into a tuple (11, 2), or returns '?'."""
    if card_str == "?":
        return "?"
    try:
        value, suit = card_str.strip("()").split(",")
        return int(value), int(suit)
    except Exception as e:
        print(f"[ERROR_CLIENT_UTILS_] Failed to parse card string: {card_str} -> {e}")
        return "?"
def get_player_count():
    """Get the number of players for single-player mode (2-4)."""
    while True:
        try:
            num_players = int(input("Enter the number of players (2-4): ").strip())
            if 2 <= num_players <= 4:
                return num_players
            else:
                print("Invalid number. Please enter a value between 2 and 4.")
        except ValueError:
            print("Invalid input. Please enter a number.")
def handle_server_messages(client):
    """ Continuously receive updates from the server without blocking input. """
    print("[DEBUG_CLIENT_UTILS_handle_server_messages] Entering handle_server_messages")
    try:
        while True:
            try:
                game_state = receive_json(client)
                print(f"[DEBUG_CLIENT_UTILS_handle_server_messages] Received message from server: {game_state}")

                if not game_state:
                    print("[ERROR_CLIENT_UTILS_] Server closed the connection. Exiting...")
                    sys.exit(0)

                match game_state.get("command"):
                    case "waiting":
                        print("[DEBUG_CLIENT_UTILS_handle_server_messages] Server says waiting for more players...")

                    case "host_control":
                        print("[DEBUG_CLIENT_UTILS_handle_server_messages] You are the host! Waiting for your input...")
                        print("Type 'start' to begin the game.")
                        handle_host_input(client)
                    case "game_over":
                        print("[INFO] Game over received. Exiting handler.")
                        break
                    case "start":
                        print("[DEBUG_CLIENT_UTILS_handle_server_messages] Game started! Entering game loop...")
                        continue

                    case "your_turn":
                        print("[DEBUG_CLIENT_UTILS_handle_server_messages] Received your_turn signal (turn confirmed)")

                    case "tell":
                        print(f"[INFO] {game_state.get('message')}")

                    case "message":
                        print(f"[UPDATE_CLIENT_UTILS_handle_server_messages] {game_state.get('data')}")

                    case "prompt":
                        prompt_type = game_state.get("type", "generic")
                        message = game_state.get("data", "Enter your choice:")
                        print(message)
                        player_input = input(">> ").strip()
                        send_json(client, {
                            "command": "response",
                            "type": prompt_type,
                            "data": player_input
                        })

                    case "game_state":
                        player_name = game_state.get("player_name")
                        current_turn = game_state.get("turn")
                        if player_name and current_turn:
                            if current_turn == player_name:
                                print(f"[DEBUG_CLIENT_UTILS_handle_server_messages] {player_name}, it's your turn!")

                                readable_cards = [
                                    "?" if card == "?" else Deck.card_to_string(parse_card_string(card))
                                    for card in game_state.get("your_cards", [])
                                ]
                                print(f"\nYour cards: {readable_cards}")
                                print(f"Available actions: {', '.join(game_state.get('actions', []))}")
                                action = input("Choose an action: ").strip()
                                send_json(client, {"command": "action", "data": action})
                            else:
                                print(f"[DEBUG_CLIENT_UTILS_handle_server_messages] Waiting for {current_turn} to play...")

                    case _:
                        print("[WARNING_CLIENT_UTILS_handle_server_messages] Unknown command received.")
                        print("[UPDATE_CLIENT_UTILS_handle_server_messages] Game State:", game_state)

            except (ConnectionAbortedError, ConnectionResetError):
                print("[ERROR_CLIENT_UTILS_handle_server_messages] Connection lost with server.")
                sys.exit(0)

            except Exception as e:
                print(f"[ERROR_CLIENT_UTILS_handle_server_messages] Unexpected issue in server communication: {e}")

    except (EOFError, SystemExit):
        print("[EXIT] handle_server_messages - Exiting due to connection loss.")
    print("[DEBUG_CLIENT_UTILS_] Exiting handle_server_messages")




def run_singleplayer_game(num_players):
    """Run Rats! in single-player mode (fully text-based)."""
    print("\nStarting Single Player Mode...")

    players = [Player(f"Player {i+1}", is_human=True) for i in range(num_players)]
    game = Game(players)

    run_cli_game(game)

def run_cli_game(game):
    """Runs the game in command-line mode."""
    print("\nWelcome to Rats! (CLI Mode)")

    while not game.game_over:
        current_player = game.players[game.turn]

        print(f"\n{current_player.name}'s turn!")

        # Show opponent hands based on what the player knows
        print("\nOpponent Hands (As You Remember Them):")
        for opponent in game.players:
            if opponent != current_player:
                known_hand = current_player.get_known_opponent_hand(opponent)
                readable_known_hand = [
                    Deck.card_to_string(card) if isinstance(card, tuple) else "?"
                    for card in known_hand]
                print(f"{opponent.name}: {readable_known_hand}")

        # Show the player's own hand
        print(f"\nYour cards: {[Deck.card_to_string(card) for card in current_player.get_visible_cards(current_player.name)]}")
        print("Available actions:", ", ".join(game.get_available_actions()))

        action = input("Choose an action: ").strip().lower()
        if action in game.get_available_actions():
            game.perform_action(current_player, action)
        else:
            print("Invalid action. Try again.")

    print("\nGame Over!")
    for player in game.players:
        print(f"{player.name}: {player.get_total_score()} points")
    winner = min(game.players, key=lambda p: p.get_total_score())
    print(f"{winner.name} wins!")

def run_multiplayer_client():
    """Handles client-side multiplayer connection to the server."""
    print("[DEBUG_CLIENT_UTILS_] Entering run_multiplayer_client")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_HOST, SERVER_PORT))
        print("[DEBUG_CLIENT_UTILS_] Connected to server.")

        #   Start listening for server messages in a separate thread
        thread = threading.Thread(target=handle_server_messages, args=(client,), daemon=False)
        thread.start()

        game_state = receive_json(client)
        if game_state and game_state.get("command") == "host_control":
            print("[DEBUG_CLIENT_UTILS_] You are the host!")
            threading.Thread(target=handle_host_input, args=(client,), daemon=True).start()
        else:
            print("[DEBUG_CLIENT_UTILS_] Waiting for the host to start the game...")

        #   Wait for server thread to finish (game over or disconnect)
        thread.join()

    except ConnectionRefusedError:
        print("[ERROR_CLIENT_UTILS_] Could not connect to the server. Ensure the server is running.")

    except Exception as e:
        print(f"[ERROR_CLIENT_UTILS_] Unexpected error: {e}")

    finally:
        print("[DEBUG_CLIENT_UTILS_] Closing client socket...")
        try:
            client.close()
        except Exception as e:
            print(f"[ERROR_CLIENT_UTILS_] Failed to close socket: {e}")

    print("[DEBUG_CLIENT_UTILS_] Exiting run_multiplayer_client")



'''
def play_multiplayer_game(client):
    """Handles game communication after the game starts."""
    print("[DEBUG_CLIENT_UTILS_] Entering play_multiplayer_game")
    while True:
        game_state = receive_json(client)
        if not game_state:
            print("[ERROR_CLIENT_UTILS_] Disconnected from server.")
            break

        if game_state.get("command") == "start":
            print("[DEBUG_CLIENT_UTILS_] Game is starting!")
            continue

        current_player = game_state["turn"]
        player_name = game_state["player_name"]

        if current_player == player_name:
            print(f"[DEBUG_CLIENT_UTILS_] {player_name}, it's your turn!")
            readable_cards = ["?" if card == "?" else Deck.card_to_string(parse_card_string(card))
                for card in game_state["your_cards"]]
            print(f"\nYour cards: {readable_cards}")
            print("Available actions:", ", ".join(game_state["actions"]))

            action = input("Choose an action: ").strip().lower()
            if action in game_state["actions"]:
                send_json(client, {"command": "action", "data": action})
            else:
                print("Invalid action. Try again.")
        else:
            print(f"[DEBUG_CLIENT_UTILS_] Waiting for {current_player} to play...")
    print("[DEBUG_CLIENT_UTILS_] Exiting play_multiplayer_game")
    '''