import numpy as np
from collections import Counter
from deck import Deck
from player import Player
import pickle
class Game:
    def __init__(self, *players):
        self.deck = Deck()
        self.discard_pile = []
        self.last_discard = None
        self.special_action_available = False
        self.players = list(players)
        self.turn = 0
        self.rats_caller = None
        self.rats_called = False
        self.final_turn = False
        self.game_over = False
        self.turn_counter = 0
        self.deal_initial_cards()

    def deal_initial_cards(self):
        """Deal initial cards to each player at the start of the game."""
        for player in self.players:
            player.set_initial_cards(self.deck.draw(), self.deck.draw(), self.deck.draw())

    def handle_card_replacement(self, player, index, new_card):
        """Handles replacing a player's card, updating the discard pile, and clearing opponent memory if necessary."""
        if index == -1:
            self.discard_pile.append(new_card)
            self.last_discard = new_card
            print(f"{player.name} discarded: {new_card}")
        else:
            discarded_card = player.replace_card(index, new_card)
            self.discard_pile.append(discarded_card)
            self.last_discard = discarded_card
            print(f"{player.name} replaced card {index} with {new_card} and discarded: {discarded_card}")

            # Make all opponents forget this card if they knew it
            for opponent in self.players:
                if opponent != player and player.name in opponent.card_known_by[index]:
                    print(f"DEBUG BEFORE: {opponent.name}'s memory of {player.name}'s hand: {opponent.get_known_opponent_hand(player)}")
                    opponent.forget_opponent_card(player.name, index)
                    print(f"DEBUG AFTER: {opponent.name}'s memory of {player.name}'s hand: {opponent.get_known_opponent_hand(player)}")
        # Handle special actions (Jack or Queen)
        if self.last_discard == "J":
            print(f"{player.name} discarded a Jack! You may peek at a card.")
            self.ask_peek_choice(player)
        elif self.last_discard == "Q":
            print(f"{player.name} discarded a Queen! Special action: Swap.")
            self.swap_with_queen_human(player)

    def get_available_actions(self):
        """Returns a list of available actions for the current player."""
        return ["draw", "call_rats"]

    def perform_action(self, player, action, client_socket=None, send_to_all=None):
        """Performs the specified action for the current player and sends updates to clients if in multiplayer."""
        print(f"DEBUG: Performing action '{action}' for {player.name}")

        if len(self.deck.cards) == 0:
            message = "Deck is empty. Ending the game."
            if client_socket:
                client_socket.sendall(pickle.dumps({"command": "message", "data": message}))
            else:
                print(message)
            self.end_game()
            return

        if self.rats_caller and self.players[self.turn].name == self.rats_caller:
            message = f"{self.players[self.turn].name} has completed their final turn. Ending the game."
            if client_socket:
                client_socket.sendall(pickle.dumps({"command": "message", "data": message}))
            else:
                print(message)
            self.end_game()
            return

        if action == "draw":
            self.draw_human(player, client_socket)

        elif action == "call_rats":
            self.call_rats()

    # ✅ Notify all players that the turn has changed
        self.advance_turn(client_socket, send_to_all)
        print(f"DEBUG: Ending action '{action}' for {player.name}. Next turn: {self.players[self.turn].name}")

    def draw_human(self, player, client_socket=None):
        """Handles drawing a card for the player (single-player or multiplayer)."""
        drawn_card = self.deck.draw()
        if not drawn_card:
            message = "Deck is empty. Cannot draw."
            if client_socket:
                client_socket.sendall(pickle.dumps({"command": "message", "data": message}))
            else:
                print(message)
            return

        message = f"You drew: {drawn_card}"
        if client_socket:
            client_socket.sendall(pickle.dumps({"command": "message", "data": message}))  # ✅ Send draw message
        else:
            print(message)

    # ✅ Multiplayer: Ask which card to replace
        if client_socket:
            client_socket.sendall(pickle.dumps({"command": "prompt", "data": "Choose which card to replace (0, 1, 2) or -1 to discard:"}))
            response_data = client_socket.recv(4096)
            replace_index = int(pickle.loads(response_data))
        else:
            replace_index = int(input("Choose which card to replace (0, 1, 2) or -1 to discard: "))

    # ✅ Process choice
        if replace_index == -1:
            message = f"{player.name} discarded {drawn_card}."
        elif 0 <= replace_index < len(player.cards):
            message = f"{player.name} replaced card {replace_index} with {drawn_card}."
            player.cards[replace_index] = drawn_card  # ✅ Perform card replacement
        else:
            message = "Invalid choice. Please choose 0, 1, 2, or -1."
    
        if client_socket:
            client_socket.sendall(pickle.dumps({"command": "message", "data": message}))  # ✅ Confirm card replacement
        else:
            print(message)

    def swap_with_queen_human(self, player):
        """Handles swapping a card when a Queen is discarded while ensuring that knowledge remains player-specific."""
        print("\nChoose an opponent to swap with:")
        opponents = [opponent for opponent in self.players if opponent != player]

        for i, opponent in enumerate(opponents):
            print(f"{i}: {opponent.name}")

        while True:
            try:
                opp_index = int(input("Enter the number of the opponent to swap with: "))
                if 0 <= opp_index < len(opponents):
                    opponent = opponents[opp_index]
                    break
                else:
                    print("Invalid choice. Choose a valid opponent.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        # Player selects a card to give
        print(f"{player.name}, choose a card to give to {opponent.name}:")
        for i, card in enumerate(player.cards):
            display_value = card if player.revealed_cards[i] else "?"
            print(f"{i}: {display_value}")  # Player only sees their own knowledge

        give_index = int(input("Enter the index of the card to give: "))

        # Player selects a card to take
        print(f"{player.name}, choose a card to take from {opponent.name}:")
        for i, card in enumerate(opponent.cards):
            display_value = opponent.get_visible_cards(player.name)[i]  # Show only known cards
            print(f"{i}: {display_value}")

        while True:
            try:
                take_index = int(input("Enter the index of the card to take: "))
                if 0 <= take_index < len(opponent.cards):
                    break
                else:
                    print("Invalid choice. Choose 0, 1, or 2.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        # Swap the cards
        player.cards[give_index], opponent.cards[take_index] = opponent.cards[take_index], player.cards[give_index]

        # **Knowledge Transfer Rules:**
        # 1. The player KNOWS they gave this card away, so the opponent must know they have it.
        opponent.reveal_card_to(take_index, player.name)

        # 2. The player does NOT know what they received unless they already knew it before.
        if take_index not in player.known_opponent_cards.get(opponent.name, {}):
            player.revealed_cards[give_index] = False  # Hide the received card from the player

        # 3. The opponent does NOT know what they received unless they already knew it before.
        if give_index not in opponent.known_opponent_cards.get(player.name, {}):
            opponent.revealed_cards[take_index] = False  # Hide the received card from the opponent

        print(f"{player.name} swapped a card with {opponent.name}. Only logical knowledge is transferred.")


    def ask_peek_choice(self, player):
        """Allows the player to choose whether to peek at their own card or an opponent's."""
        while True:
            print("Do you want to:")
            print("1: Peek at one of your own cards")
            print("2: Peek at one of your opponent's cards")

            choice = input("Enter 1 or 2: ").strip()
            if choice == "1":
                self.peek_self(player)
                break
            elif choice == "2":
                self.peek_opponent(player)
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")

    def peek_opponent(self, player):
        """Allows the player to peek at an opponent's card and remember it."""
        print("\nChoose an opponent to peek at:")
        opponents = [opponent for opponent in self.players if opponent != player]

        for i, opponent in enumerate(opponents):
            print(f"{i}: {opponent.name}")

        while True:
            try:
                opp_index = int(input("Enter the number of the opponent to peek at: "))
                if 0 <= opp_index < len(opponents):
                    opponent = opponents[opp_index]
                    break
                else:
                    print("Invalid choice. Choose a valid opponent.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        print(f"{opponent.name}'s cards (as you remember them):")
        for i in range(3):
            display_value = opponent.cards[i] if player.name in opponent.card_known_by[i] else "?"
            print(f"{i}: {display_value}")  # **Show known cards, hide unknown ones**

        while True:
            try:
                peek_index = int(input(f"Choose an opponent's card to peek at (0, 1, or 2): "))
                if 0 <= peek_index < len(opponent.cards):
                    print(f"You peeked at {opponent.name}'s card: {opponent.cards[peek_index]}")
                    opponent.reveal_card_to(peek_index, player.name)  # Player now knows this card
                    break
                else:
                    print("Invalid choice. Choose 0, 1, or 2.")
            except ValueError:
                print("Invalid input. Please enter a number.")


    def call_rats(self):
        """Handles the 'Rats' call and sets up the final turn."""
        print(f"{self.players[self.turn].name} calls 'Rats'!")
        self.rats_called = True
        self.rats_caller = self.players[self.turn].name
        print(f"{self.players[(self.turn + 1) % len(self.players)].name} gets one final turn!")

    def advance_turn(self, client_socket=None, send_to_all=None):
        """Advances the turn to the next player and updates clients if in multiplayer."""
        self.turn = (self.turn + 1) % len(self.players)
        message = f"Turn has advanced to: {self.players[self.turn].name}"

        if send_to_all:
            send_to_all({"command": "message", "data": message})  # ✅ Notify all players
        else:
            print(message)
            
    def end_game(self):
        """Handles scoring and ends the game."""
        scores = [player.get_total_score() for player in self.players]
        winner = min(self.players, key=lambda p: p.get_total_score())
        print(f"\nGame Over!\n {scores}")
        for player in self.players:
            print(f"{player.name}: {player.get_total_score()} points")
        print(f"{winner.name} wins!")
        self.game_over = True
