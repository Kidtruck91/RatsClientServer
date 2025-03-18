
from network_utils import send_json, receive_json

from client_utils import handle_host_input,get_player_count,run_singleplayer_game,run_multiplayer_client
SERVER_HOST = "ratsmpserver.ddns.net"
SERVER_PORT = 5555

def main():
    """Game startup menu allowing choice between single-player, multiplayer, or exit."""
    print("[ENTER] main()")

    while True:
        print("\nWelcome to Rats!")
        print("1: Single Player")
        print("2: Multiplayer")
        print("3: Exit")

        choice = input("Enter your choice: ").strip()
        print(f"[DEBUG] User selected: {choice}")

        if choice == "1":
            num_players = get_player_count()
            print(f"[DEBUG] Running singleplayer with {num_players} players.")
            run_singleplayer_game(num_players)
        elif choice == "2":
            print("[DEBUG] Running multiplayer client.")
            run_multiplayer_client()
        elif choice == "3":
            print("[DEBUG] Exiting client.")
            break
        else:
            print("[ERROR] Invalid input.")

    print("[EXIT] main()")










if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] Client crashed: {e}")
