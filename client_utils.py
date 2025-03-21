import threading
import socket
import time
import json
import sys
from network_utils import send_json, receive_json,send_to_server
from game_logic import Game, Player,Deck
SERVER_HOST = "ratsmpserver.ddns.net"  # Replace with actual server IP
SERVER_PORT = 5555

def handle_host_input(client):
    """Allows the host to start the game when ready, but only if there are at least 2 players."""
    print("[DEBUG] Entering handle_host_input")
    
    while True:
        print("Type 'start' to begin the game (minimum 2 players required).")
        
        # ✅ Check the number of players before allowing "start"
        game_state = receive_json(client)
        if game_state.get("command") == "waiting":
            players = game_state.get("players", [])
            print(f"[DEBUG] Current players: {players}")

            if len(players) < 2:
                print("[ERROR] At least 2 players are required to start the game.")
                time.sleep(2)  # ✅ Prevent spam, wait before checking again
                continue  # ✅ Keep checking until enough players join

        command = input(">> ").strip().lower()
        if command == "start":
            send_to_server(client, {"command": "start_game"})
            print("[DEBUG] Sent start command to server.")
            break  # ✅ Prevents infinite loop

        print("[ERROR] Invalid command. Type 'start' to begin the game.")


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
    print("[DEBUG] Entering handle_server_messages")
    try:
        while True:
            try:
                game_state = receive_json(client)
                print(f"[DEBUG] Received message from server: {game_state}")  # ✅ Debugging received data

                if not game_state:
                    print("[ERROR] Server closed the connection. Exiting...")
                    sys.exit(0)

                # ✅ Handle "waiting" message correctly
                if game_state.get("command") == "waiting":
                    print("[DEBUG] Server says waiting for more players...")
                    continue  # ✅ Stay connected and wait for the next update

                # ✅ Handle "host_control" message correctly
                if game_state.get("command") == "host_control":
                    print("[DEBUG] You are the host! Waiting for your input...")
                    print("Type 'start' to begin the game.")

                    # ✅ CALL handle_host_input(client) so the host can type
                    handle_host_input(client)  
                    continue  # ✅ Stay connected
                if game_state.get("command") == "prompt":
                    print(game_state["data"])  # ✅ Display the prompt message
                    player_input = input(">> ").strip()
                    send_json(client, {"command": "response", "data": player_input})
                    continue  # ✅ Stay connected
                if game_state.get("command") == "game_state":
                    if "player_name" not in game_state:
                        print(f"[ERROR] Missing 'player_name' in game state! Data: {game_state}")

                    print(f"[DEBUG] Game state received: {game_state}")
                # ✅ Handle "start" message correctly
                if game_state.get("command") == "start":
                    print("[DEBUG] Game started! Entering game loop...")
                    play_multiplayer_game(client)
                    break  # ✅ Exit the loop after game starts

                print("[UPDATE] Game State:", game_state)  # ✅ Debugging all other messages
            
            except ConnectionAbortedError:
                print("[ERROR] Connection was aborted. Server may have closed the connection.")
                sys.exit(0)

            except ConnectionResetError:
                print("[ERROR] Connection reset by server.")
                sys.exit(0)

            except Exception as e:
                print(f"[ERROR] Unexpected issue in server communication: {e}")

    except (EOFError, SystemExit):
        print("[EXIT] handle_server_messages - Exiting due to connection loss.")
    print("[DEBUG] Exiting handle_server_messages")



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
                print(f"{opponent.name}: {known_hand}")

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

def run_multiplayer_clientv2():
    """Handles client-side multiplayer connection to the server."""
    print("\nStarting Multiplayer Mode...")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_HOST, SERVER_PORT))
        print("[DEBUG] Connected to server.")

        # Start listening for server messages
        threading.Thread(target=handle_server_messages, args=(client,), daemon=True).start()

        # Receive initial game state
        game_state = receive_json(client)
        print(f"[DEBUG] Received game state: {game_state}")
        if game_state and game_state.get("command") == "host_control":
            print("[DEBUG] This player is the host.")
            handle_host_input(client)  # ✅ Call it directly instead of threading
        
        else:
            print("[DEBUG] Waiting for the host to start the game...")

    except ConnectionRefusedError:
        print("Could not connect to the server. Ensure the server is running.")

    finally:
        client.close()

def run_multiplayer_client():
    """Handles client-side multiplayer connection to the server."""
    print("[DEBUG] Entering run_multiplayer_client")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_HOST, SERVER_PORT))
        print("[DEBUG] Connected to server.")

        # ✅ Start listening for server messages in a separate thread
        threading.Thread(target=handle_server_messages, args=(client,), daemon=True).start()

        game_state = receive_json(client)
        if game_state and game_state.get("command") == "host_control":
            print("[DEBUG] You are the host!")
            
            print("[DEBUG] Starting handle_host_input thread...")
            # ✅ Start a separate thread for host input so it doesn’t block
            threading.Thread(target=handle_host_input, args=(client,), daemon=True).start()

        else:
            print("[DEBUG] Waiting for the host to start the game...")

        # ✅ Keep the main thread alive so the client doesn’t exit immediately
        while True:
            pass  

    except ConnectionRefusedError:
        print("[ERROR] Could not connect to the server. Ensure the server is running.")
    
    finally:
        print("[DEBUG] Closing client socket...")
        client.close()
    print("[DEBUG] Exiting run_multiplayer_client")


def play_multiplayer_game(client):
    """Handles game communication after the game starts."""
    print("[DEBUG] Entering play_multiplayer_game")
    while True:
        game_state = receive_json(client)
        if not game_state:
            print("[ERROR] Disconnected from server.")
            break

        if game_state.get("command") == "start":
            print("[DEBUG] Game is starting!")
            continue

        current_player = game_state["turn"]
        player_name = game_state["player_name"]

        if current_player == player_name:
            print(f"[DEBUG] {player_name}, it's your turn!")
            print(f"Your cards: {game_state['your_cards']}")
            print("Available actions:", ", ".join(game_state["actions"]))

            action = input("Choose an action: ").strip().lower()
            if action in game_state["actions"]:
                send_json(client, {"command": "action", "data": action})
            else:
                print("Invalid action. Try again.")
        else:
            print(f"[DEBUG] Waiting for {current_player} to play...")
    print("[DEBUG] Exiting play_multiplayer_game")