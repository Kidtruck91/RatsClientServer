import unittest
import json
from game_logic import Game, Player
from deck import Deck

class TestMultiplayerGame(unittest.TestCase):
    def setUp(self):
        """Set up a controlled multiplayer game with two clients."""
        print("\n🔍 Setting Up Multiplayer Game Simulation...")

        self.players = [Player("Player 1"), Player("Player 2")]
        self.game = Game(players=self.players)
        
        print("\n🎲 Initial Hands:")
        for player in self.players:
            print(f"{player.name}: {[Deck.card_to_string(card) for card in player.cards]}")

    def simulate_turn(self, player, action, replace_index=None):
        """Simulates a turn for a player, applying actions and verifying state updates."""
        print(f"\n🎲 {player.name}'s Turn!")

        # Encode game state
        game_state = {
            "command": "game_state",
            "data": {
                "turn": self.game.players[self.game.turn].name,
                "your_cards": [Deck.card_to_string(card) if isinstance(card, tuple) else card for card in player.get_visible_cards()],
                "actions": self.game.get_available_actions(),
                "discard_pile": [Deck.card_to_string(card) if isinstance(card, tuple) else card for card in self.game.discard_pile]
            }
        }

        # Send "game state" to the "client" (simulation)
        json_data = json.dumps(game_state)
        print(f"[SERVER] Sent JSON Data:\n{json.dumps(json.loads(json_data), indent=2)}")

        # Simulate client receiving game state
        received_game_state = json.loads(json_data)
        print(f"[CLIENT] Received JSON Data:\n{json.dumps(received_game_state, indent=2)}")

        # Simulate player choosing an action
        if action == "draw":
            print(f"\n{player.name} chooses to draw.")
            drawn_card, replace_index = self.game.draw_human(player)  # Simulate drawing a card
            self.game.handle_card_replacement(player, replace_index, drawn_card)
        elif action == "call_rats":
            print(f"\n{player.name} calls 'Rats!'")
            self.game.call_rats()

        # Advance the turn
        self.game.advance_turn()

    def test_full_multiplayer_game(self):
        """Simulates a full game with two players taking turns."""
        print("\n🚀 Starting Multiplayer Game Simulation...\n")

        # Simulate turns for both players
        self.simulate_turn(self.players[0], "draw", replace_index=0)
        self.simulate_turn(self.players[1], "draw", replace_index=1)
        self.simulate_turn(self.players[0], "call_rats")  # Player 1 calls Rats!
        self.simulate_turn(self.players[1], "draw", replace_index=2)  # Final turn for Player 2

        print("\n🏆 Game Over! Final Scores:")
        for player in self.players:
            print(f"{player.name}: {player.get_total_score()} points")
        winner = min(self.players, key=lambda p: p.get_total_score())
        print(f"\n🎉 {winner.name} wins!")

if __name__ == "__main__":
    unittest.main()
