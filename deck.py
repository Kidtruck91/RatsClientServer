import random

class Deck:
    def __init__(self):
        self.cards = self.create_deck()
        random.shuffle(self.cards)

    def create_deck(self):
        # Create a standard 52-card deck with Kings (K), Jacks (J), and Queens (Q)
        deck = []
        for value in range(1, 14):  # 1 to 13
            if value == 11:  # Jack
                card_value = 'J'
            elif value == 12:  # Queen
                card_value = 'Q'
            elif value == 13:  # King
                card_value = 'K'
            else:
                card_value = value
            deck.extend([card_value] * 4)  # 4 of each value (one per suit)
        return deck

    def draw(self):
        return self.cards.pop() if self.cards else None
