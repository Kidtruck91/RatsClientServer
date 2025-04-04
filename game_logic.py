import numpy as np
from collections import Counter
from deck import Deck
from player import Player
from network_utils import send_to_client, send_to_all, send_json, receive_json

class Game:
    
    def __init__(self, players=None, discard_pile=None, draw_pile=None, turn=0):
        """Initializes a new game or clones an existing game."""
        self.players = list(players) if players else []
        self.discard_pile = discard_pile[:] if discard_pile else []
        self.draw_pile = draw_pile[:] if draw_pile else Deck().cards[:]  # Preserve deck order
        self.turn = turn
        self.rats_caller = None
        self.rats_called = False
        self.final_turn = False
        self.game_over = False
        self.turn_counter = 0
        self.last_discard = None
        self.special_action_available = False
        self.pending_prompts = {} 

        #   If this is a fresh game (not a clone), create a deck and deal cards
        if not discard_pile and not draw_pile:
            self.draw_pile = Deck().cards[:] 
            self.deal_initial_cards()

    @classmethod
    def from_existing(cls, existing_game):
        """Creates a deep copy of an existing Game object."""
        return cls(
            players=[Player(p.name, p.cards[:]) for p in existing_game.players],  # Clone players
            discard_pile=existing_game.discard_pile[:],  #Clone discard pile
            draw_pile=existing_game.draw_pile[:],  #Clone deck order
            turn=existing_game.turn
        )


    def deal_initial_cards(self):
        """Deal initial cards to each player at the start of the game."""
        for player in self.players:
            if not player.cards:  # ✅ Only assign cards if the player has none
                card1, card2, card3 = self.draw_pile.pop(), self.draw_pile.pop(), self.draw_pile.pop()
                player.set_initial_cards(card1, card2, card3)
                print(f"DEBUG: {player.name} received initial cards: {[Deck.card_to_string(card) for card in player.cards]}")

    def handle_card_replacement(self, player, index, new_card):
        """Handles replacing a player's card, updating the discard pile, and clearing opponent memory if necessary."""
        print(f"DEBUG: Entering handle_card_replacement() for {player.name}. Index: {index}, New Card: {new_card}")
        print(f"DEBUG: {player.name}'s hand BEFORE replacement: {player.cards}")  #   Track pre-replacement state
        if index == -1:
            self.discard_pile.append(new_card)
            self.last_discard = new_card
            print(f"{player.name} discarded: {new_card}")
            print(f"{new_card} was placed at the top of the discard pile.")
        else:
            discarded_card = player.cards[index]
            player.cards[index] = new_card
            self.discard_pile.append(discarded_card)
            self.last_discard = discarded_card
            print(f"{player.name} replaced the {discarded_card} at position {index} with a {new_card}.")
            print(f"{discarded_card} was placed at the top of the discard pile.") 

            # Make all opponents forget this card if they knew it
            for opponent in self.players:
                if opponent != player and player.name in opponent.card_known_by[index]:
                    print(f"DEBUG BEFORE: {opponent.name}'s memory of {player.name}'s hand: {opponent.get_known_opponent_hand(player)}")
                    opponent.forget_opponent_card(player.name, index)
                    print(f"DEBUG AFTER: {opponent.name}'s memory of {player.name}'s hand: {opponent.get_known_opponent_hand(player)}")
        print(f"DEBUG: Last discarded card = {self.last_discard} (Type: {type(self.last_discard)})")
        # Handle special actions (Jack or Queen)
        if isinstance(self.last_discard, tuple):
            value, suit = self.last_discard  # Extract numeric value
            if value == 11:
                print(f"{player.name} discarded a Jack! You may peek at a card.")
                self.ask_peek_choice(player)
            elif value == 12:
                print(f"{player.name} discarded a Queen! Special action: Swap.")
                self.swap_with_queen_human(player)

    def get_available_actions(self):
        """Returns a list of available actions for the current player."""
        return ["draw", "call_rats"]

    def perform_action(self, player, action, client_socket=None, send_to_all=None):
        """Performs the specified action for the current player and sends updates to clients if in multiplayer."""
        print(f"DEBUG: Performing action '{action}' for {player.name}")

        if len(self.draw_pile) == 0:
            message = "Deck is empty. Ending the game."
            if client_socket:
                send_json(client_socket, {"command": "message", "data": message})
            else:
                print(message)
            self.end_game()
            return

        if self.rats_caller and self.players[self.turn].name == self.rats_caller:
            message = f"{self.players[self.turn].name} has completed their final turn. Ending the game."
            if client_socket:
                send_json(client_socket, {"command": "message", "data": message})
            else:
                print(message)
            self.end_game()
            return

        if action == "draw":
            drawn_card, tell_msg, prompt_msg = self.draw_human(player, client_socket)

            if drawn_card is None:
                return

            if client_socket:
                # Queue these messages and wait for response in handle_client
                send_json(client_socket, tell_msg)
                send_json(client_socket, prompt_msg)

                # Store this pending prompt context somewhere (example below)
                self.pending_prompts[player.name] = {
                    "type": "card_replacement",
                    "card": drawn_card,
                }

                return  # Wait for handle_client() to finish on response

            else:
                # Single-player: already handled
                self.handle_card_replacement(player, prompt_msg, drawn_card)


        elif action == "call_rats":
            self.call_rats()

    #   Notify all players that the turn has changed
        self.advance_turn(client_socket, send_to_all)
        print(f"DEBUG: Ending action '{action}' for {player.name}. Next turn: {self.players[self.turn].name}")

    def draw_human(self, player, client_socket=None):
        """Draws a card and returns a prompt context for replacement (multiplayer safe)."""
        if not self.draw_pile:
            print(f"{player.name} attempted to draw, but the deck is empty!")
            return None, None, None

        drawn_card = self.draw_pile.pop()
        card_str = Deck.card_to_string(drawn_card)
        print(f"{player.name} drew a {card_str}")

        if client_socket:
            # Do not block for input — just return prompt context
            tell_message = {"command": "tell", "message": f"You drew a {card_str}"}
            prompt_message = {
                "command": "prompt",
                "type": "card_replacement",
                "data": "Choose which card to replace (0, 1, 2) or -1 to discard:",
                "card_drawn": str(drawn_card),  # Optional: for logging/debug
            }
            return drawn_card, tell_message, prompt_message
        else:
            # Single-player fallback
            replace_index = int(input("Choose which card to replace (0, 1, 2) or -1 to discard: "))
            return drawn_card, None, replace_index
    
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
            display_value = card if player.name in opponent.card_known_by[i] else "?"  # Show only known cards
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
        # 1. The player KNOWS they gave this card away, so the opponent must know they have it and the opponent knows what they gave away.
        opponent.reveal_card_to(take_index, player.name)
        player.reveal_card_to(give_index, opponent.name)
        # 2. The player does NOT know what they received unless they already knew it before.
        if player.name not in opponent.card_known_by[take_index]:  #   Check if the player previously saw this card
            player.revealed_cards[give_index] = False  # Hide the received card from the player

        # 3. The opponent does NOT know what they received unless they already knew it before.
        if opponent.name not in player.card_known_by[give_index]:  #   Corrected to track card knowledge properly
            opponent.revealed_cards[take_index] = False   # Hide the received card from the opponent

        print(f"{player.name} swapped a card with {opponent.name}. Only logical knowledge is transferred.")


    def ask_peek_choice(self, player, client_socket=None):
        """Prompt player to choose peek type when discarding a Jack."""
        if client_socket:
            send_json(client_socket, {
                "command": "prompt",
                "type": "jack_peek_choice",
                "data": "Peek at your own card (1) or opponent’s card (2)?"
            })
            self.pending_prompts[player.name] = {
                "type": "jack_peek_choice"
            }
        else:
            # Single-player fallback
            while True:
                choice = input("Enter 1 to peek at your own card or 2 to peek at an opponent’s card: ").strip()
                if choice == "1":
                    self.peek_self(player)
                    break
                elif choice == "2":
                    self.peek_opponent(player)
                    break
                else:
                    print("Invalid input.")

    def peek_opponent(self, player, client_socket=None):
        opponents = [op for op in self.players if op != player]
        if client_socket:
            opponent_list = {str(i): op.name for i, op in enumerate(opponents)}
            send_json(client_socket, {
                "command": "prompt",
                "type": "peek_opponent_select",
                "data": f"Choose opponent to peek at: {opponent_list}"
            })
            self.pending_prompts[player.name] = {
                "type": "peek_opponent_select",
                "options": opponent_list,
                "opponents": opponents
            }
        else:
            # Fallback for local
            index = int(input("Select opponent: "))
            target = opponents[index]
            peek_index = int(input("Which card to peek at (0–2)? "))
            player.add_known_opponent_card(target.name, peek_index, target.cards[peek_index])
            print(f"You peeked at {target.name}'s card: {Deck.card_to_string(target.cards[peek_index])}")

    def peek_self(self, player, client_socket=None):
        if client_socket:
            send_json(client_socket, {
                "command": "prompt",
                "type": "peek_self_index",
                "data": "Choose a card to peek at (0, 1, 2):"
            })
            self.pending_prompts[player.name] = {
                "type": "peek_self_index"
            }
        else:
            index = int(input("Which card to peek at? (0–2): "))
            card = player.cards[index]
            player.revealed_cards[index] = True
            print(f"You peeked at your card: {Deck.card_to_string(card)}")
                
    def call_rats(self, client_socket=None, send_to_all=None):
        """Handles the 'Rats' call and sets up the final turn."""
        print(f"{self.players[self.turn].name} calls 'Rats'!")
        self.rats_called = True
        self.rats_caller = self.players[self.turn].name
        next_player = self.players[(self.turn + 1) % len(self.players)]

        if send_to_all:
            send_to_all({"command": "message", "data": f"{self.players[self.turn].name} called 'Rats'!"})

        # ✅ Send a private message to the next player
        if client_socket:
            send_to_client(client_socket, {"command": "final_turn", "message": "You have one last turn!"})

        print(f"{next_player.name} gets one final turn!")

    def advance_turn(self):
        """Advances the turn to the next player and updates clients if in multiplayer."""
        self.turn = (self.turn + 1) % len(self.players)
        
            
    def end_game(self):
        """Handles scoring and ends the game."""
        scores = [player.get_total_score() for player in self.players]
        winner = min(self.players, key=lambda p: p.get_total_score())
        print(f"\nGame Over!\n {scores}")
        for player in self.players:
            print(f"{player.name}: {player.get_total_score()} points")
        print(f"{winner.name} wins!")
        self.game_over = True
