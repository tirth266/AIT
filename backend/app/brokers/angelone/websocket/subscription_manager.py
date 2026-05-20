from typing import List, Dict

class SubscriptionManager:
    """
    Helper to manage and format subscription requests for Angel One.
    """
    def __init__(self):
        self.active_tokens = set()

    def format_subscription(self, exchange_type: int, tokens: List[str]) -> List[Dict]:
        return [{"exchangeType": exchange_type, "tokens": tokens}]

    def add_tokens(self, tokens: List[str]):
        self.active_tokens.update(tokens)

    def remove_tokens(self, tokens: List[str]):
        self.active_tokens.difference_update(tokens)
