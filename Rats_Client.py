import socket
import pickle
from game_logic import Game, Player

SERVER_HOST = "192.168.1.7"  # Replace with your actual local IP
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

        while True:
            response = pickle.loads(client.recv(4096))  # ✅ Ensure full message is received
            print(f"DEBUG: Client received: {response}")  # Debugging received data

            if response.get("command") == "host_control":
                print("\n🎮 You are the host! 🎮")
                print("Connected players:")
                for player in response["players"]:
                    print(f"- {player}")

                while True:
                    start_game = input("Type 'start' to begin the game: ").strip().lower()
                    if start_game == "start":
                        client.sendall(pickle.dumps({"start_game": True}))
                        print("DEBUG: Host sent start command")
                        break
                    print("Invalid input. Type 'start' to begin.")
                continue
            elif response.get("command") == "waiting":
                print("\nWaiting for the host to start the game...")
                print("Connected players:")
                for player in response["players"]:
                    print(f"- {player}")

            elif response.get("command") == "start":
                print("\n🎲 Game is starting!\n")
                play_multiplayer_game(client)  # ✅ Transition into the game loop
                return  # ✅ Prevents returning to the menu

    except ConnectionRefusedError:
        print("Could not connect to the server. Ensure the server is running.")

    finally:
        client.close()

def play_multiplayer_game(client):
    """Handles game communication after the game starts."""
    while True:
        try:
            response = client.recv(4096)
            game_state = pickle.loads(response)  # ✅ Ensure full game state is received
            print(f"DEBUG: Received game state: {game_state}")  # ✅ Debugging received data

            # ✅ Ensure game_state is a tuple
            if isinstance(game_state, tuple) and len(game_state) == 2:
                game, player_name = game_state
            else:
                print("ERROR: Invalid game state received!")
                continue  # Ignore bad data and wait for the next update

            current_player = game.players[game.turn]

            if current_player.name == player_name:
                print(f"\nYour turn, {current_player.name}!")
                print(f"Your cards: {current_player.get_visible_cards()}")  # Show only player's cards
                print("Available actions:", ", ".join(game.get_available_actions()))

                action = input("Choose an action: ").strip().lower()
                if action in game.get_available_actions():
                    client.sendall(pickle.dumps(action))  # ✅ Send action to server
                else:
                    print("Invalid action. Try again.")

            else:
                print(f"\nWaiting for {current_player.name} to play...")

        except (ConnectionResetError, EOFError, pickle.UnpicklingError) as e:
            print(f"Disconnected from the server. Error: {e}")
            break


if __name__ == "__main__":
    main()
