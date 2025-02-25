class Player:
    def __init__(self, name, is_human=True):
        self.name = name
        self.is_human = is_human
        self.cards = []
        self.revealed_cards = [False, False, False]  # Tracks whether the player has seen their own cards
        self.card_known_by = [{}, {}, {}]  # Tracks which opponents have seen each card

    def set_initial_cards(self, card1, card2, card3):
        """Sets the player's initial hand, revealing only the outside cards to themselves."""
        self.cards = [card1, card2, card3]
        self.revealed_cards = [True, False, True]  # The player knows positions 0 and 2

    def replace_card(self, index, new_card):
        """Replaces a card in the player's hand and returns the discarded card."""
        discarded_card = self.cards[index]
        self.cards[index] = new_card
        self.revealed_cards[index] = True  # Any replaced card is now revealed

        # Reset visibility for opponents who previously saw this card
        self.card_known_by[index] = {}

        return discarded_card

    def reveal_card_to(self, index, viewer_name):
        """Marks a card as known to a specific opponent."""
        self.card_known_by[index][viewer_name] = True

    def get_visible_cards(self, viewer_name=None):
        """Returns a representation of the player's hand with hidden cards as '?' for those not known to the viewer."""
        if viewer_name is None:
            return [card if revealed else "?" for card, revealed in zip(self.cards, self.revealed_cards)]

        return [
            self.cards[i] if self.revealed_cards[i] or viewer_name in self.card_known_by[i] else "?"
            for i in range(3)
    ]
    def get_known_opponent_hand(self, opponent):
        """Returns a representation of an opponent's hand using only the player's known information."""
        return [
            opponent.cards[i] if self.name in opponent.card_known_by[i] else "?"
            for i in range(3)
    ]
    def forget_opponent_card(self, opponent_name, index):
        """Removes an opponent's card from memory when they replace it with a new drawn card."""
        if opponent_name in self.card_known_by[index]:
            del self.card_known_by[index][opponent_name]
