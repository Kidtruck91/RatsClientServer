import socket
import pickle
import sys
import threading
from game_logic import Game, Player

SERVER_HOST = "ratsmpserver.ddns.net"  # Replace with your actual local IP
SERVER_PORT = 5555

def main():
    """Game startup menu allowing choice between single-player, multiplayer, or exit."""
    while True:
        print("\nWelcome to Rats!")
        print("1: Single Player")
        print("2: Multiplayer")
        print("3: Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            num_players = get_player_count()
            run_singleplayer_game(num_players)
        elif choice == "2":
            run_multiplayer_client()
        elif choice == "3":
            print("Exiting the game. Goodbye!")
            break
        else:
            print("Invalid input. Please enter 1, 2, or 3.")

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

def run_singleplayer_game(num_players):
    """Run Rats! in single-player mode (fully text-based)."""
    print("\nStarting Single Player Mode...")

    players = [Player(f"Player {i+1}", is_human=True) for i in range(num_players)]
    game = Game(*players)

    run_cli_game(game)

def run_cli_game(game):
    """Runs the game in command-line mode."""
    print("\nWelcome to Rats! (CLI Mode)")

    while not game.game_over:
        current_player = game.players[game.turn]

        print(f"\n{current_player.name}'s turn!")

        # **Show opponent hands based on what the player knows**
        print("\nOpponent Hands (As You Remember Them):")
        for opponent in game.players:
            if opponent != current_player:
                known_hand = current_player.get_known_opponent_hand(opponent)  # Pass the opponent object
                print(f"{opponent.name}: {known_hand}")

        # **Show the player's own hand**
        print(f"\nYour cards: {current_player.get_visible_cards(current_player.name)}")
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
    print("\nStarting Multiplayer Mode...")

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_HOST, SERVER_PORT))

        # Start a separate thread to listen for server updates
        threading.Thread(target=handle_server_messages, args=(client,), daemon=True).start()

        # If this player is the host, allow them to start the game
        print("\nType 'start' to begin the game (only for host).")
        is_host = False  # Default to non-host

        # Wait for initial message from server
        game_state = client.recv(4096)
        if game_state:
            try:
                game_data = pickle.loads(game_state)  # Ensure game_data is properly received
                if isinstance(game_data, dict) and "host_control" in game_data.get("command", ""):
                    is_host = True  # This client is the host
            except pickle.UnpicklingError:
                print("Error: Could not parse game data from server.")


        threading.Thread(target=handle_host_input, args=(client, is_host)).start()


        # Keep the main thread alive
        while True:
            pass

    except ConnectionRefusedError:
        print("Could not connect to the server. Ensure the server is running.")

    finally:
        client.close()
def play_multiplayer_game(client):
    """Handles game communication after the game starts."""
    while True:
        try:
            response = client.recv(4096)
            game_state = pickle.loads(response)  
            print(f"DEBUG: Received game state: {game_state}")  

            # ✅ Handle messages separately
            if isinstance(game_state, dict):
                if game_state.get("command") == "message":
                    print(game_state["data"])  # ✅ Display message to the player
                    continue  # ✅ Skip normal game state processing
                
                elif game_state.get("command") == "prompt":
                    print(game_state["data"])  # ✅ Show prompt message
                    response = input(">>> ")  # ✅ Player provides input
                    client.sendall(pickle.dumps(response))
                    continue  # ✅ Skip normal game state processing

            # ✅ Ensure game_state is a tuple for normal game updates
            if isinstance(game_state, tuple) and len(game_state) == 2:
                game, player_name = game_state
            else:
                print("ERROR: Invalid game state received!")
                continue  

            current_player = game.players[game.turn]

            if current_player.name == player_name:
                print(f"\nYour turn, {current_player.name}!")
                print(f"Your cards: {current_player.get_visible_cards()}")  
                print("Available actions:", ", ".join(game.get_available_actions()))

                action = input("Choose an action: ").strip().lower()
                if action in game.get_available_actions():
                    client.sendall(pickle.dumps(action))  
                else:
                    print("Invalid action. Try again.")

            else:
                print(f"\nWaiting for {current_player.name} to play...")

        except (ConnectionResetError, EOFError, pickle.UnpicklingError) as e:
            print(f"Disconnected from the server. Error: {e}")
            break
def handle_server_messages(client):
    """ Continuously receive updates from the server without blocking input. """
    try:
        while True:
            game_state = client.recv(4096)  # Receive data from server
            if not game_state:
                print("Disconnected from the server.")
                sys.exit(0)

            try:
                # Attempt to deserialize the data
                game_data = pickle.loads(game_state)

                # Check if it's the expected object
                if isinstance(game_data, dict) and "command" in game_data:
                    print(f"\nReceived command from server: {game_data['command']}")
                    continue  # Skip processing if it's just a command message

                game, player_id = game_data  # Unpack the tuple
                print(f"DEBUG: Player {player_id} received game state. Current turn: {game.players[game.turn].name}")
                print("\nUpdated Game State:")
                for player in game.players:
                    print(f"{player.name}: {player.get_visible_cards()}")

                if game.players[game.turn].name == f"Player {player_id}":
                    print(f"\nYour turn, {game.players[game.turn].name}!")
                    print("Available actions:", ", ".join(game.get_available_actions()))
                else:
                    print(f"\nWaiting for {game.players[game.turn].name} to play...")

            except pickle.UnpicklingError:
                print("Error: Received data could not be unpickled. Possible corruption or incorrect format.")
                print(f"Raw Data Received: {game_state}")

    except (ConnectionResetError, EOFError):
        print("Server disconnected.")
        sys.exit(0)

def handle_host_input(client, is_host):
    """ Runs in a separate thread, allowing the host to start the game without blocking. """
    if not is_host:
        return
    while True:
        command = input().strip().lower()
        if command == "start":
            client.sendall(pickle.dumps({"start_game": True}))
            print("Game is starting...")
            break  # Exit the input loop after starting
        else:
            print("Invalid command. Type 'start' to begin.")

if __name__ == "__main__":
    main()
