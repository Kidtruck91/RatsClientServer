import random

class Deck:
    SUITS = ["Spades", "Clubs", "Hearts", "Diamonds"]
    VALUE_NAMES = {1: "Ace", 11: "Jack", 12: "Queen", 13: "King"}

    def __init__(self):
        """Creates a shuffled deck with all suits and values."""
        self.cards = [(value, suit) for value in range(1, 14) for suit in range(4)]
        random.shuffle(self.cards)

    @classmethod
    def fixed_deck(cls, fixed_cards):
        """Creates a deck with a predefined order instead of a shuffled deck."""
        deck = cls.__new__(cls)  
        deck.cards = list(fixed_cards)  
        return deck  

    @staticmethod
    def card_to_string(card):
        """Converts a card tuple (value, suit) into a human-readable string."""
        value, suit = card
        value_str = Deck.VALUE_NAMES.get(value, str(value))  #   Convert 1 to A, 11-13 to J/Q/K
        suit_str = Deck.SUITS[suit]  #   Convert 0-3 to suit names
        return f"{value_str} of {suit_str}"
    
    def draw(self):
        """Draws a card from the deck, or returns None if empty."""
        return self.cards.pop() if self.cards else None
