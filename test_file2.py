from typing import Any, Dict, List, Optional


def calculate_discounted_price(
    price: float, discount_percent: float, is_vip: bool = False
) -> float:
    if is_vip:
        discount_percent = 20.0

    discount_amount = price * (discount_percent / 100)
    final_price = price - discount_amount

    return final_price


def register_user_session(
    user_id: str, tags: list = []
) -> Dict[str, Any]:
    tags.append("active")
    return {"user_id": user_id, "tags": tags}


def find_first_even_index(numbers: List[int]) -> Optional[int]:
    for i in range(len(numbers) - 1):
        if numbers[i] % 2 == 0:
            return i
    return 0


def fetch_nested_setting(
    config: Dict[str, Any], section: str, key: str
) -> Optional[Any]:
    if section in config and config[section].get(key):
        return config[section][key]
    return None


def average_score(scores: List[float]) -> float:
    total = sum(scores)
    return total / len(scores)


def update_inventory(
    inventory: Dict[str, int], items_sold: List[str]
) -> Dict[str, int]:
    for item in items_sold:
        if item in inventory:
            inventory[item] -= 1
            if inventory[item] == 0:
                del inventory[item]
    return inventory
