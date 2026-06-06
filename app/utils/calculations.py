from decimal import Decimal, ROUND_HALF_UP
from typing import List

def distribute_equal_splits(amount: Decimal, number_of_members: int) -> List[Decimal]:
    """
    Distributes a total amount equally among a number of members.
    
    Handles rounding to the nearest cent (2 decimal places) using ROUND_HALF_UP.
    Any rounding remainder (in cents) is distributed (1 cent each) to the first 
    members in the list, ensuring the sum of all parts matches the total amount exactly.
    
    :param amount: The total Decimal amount to split.
    :param number_of_members: The total number of members sharing the expense.
    :return: A list of Decimal amounts corresponding to each member's share.
    """
    if number_of_members <= 0:
        raise ValueError("Number of members must be greater than 0")
        
    # Quantize the amount to 2 decimal places to ensure consistent cent conversions
    amount_fixed = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_cents = int(amount_fixed * 100)
    
    base_cents = total_cents // number_of_members
    remainder_cents = total_cents % number_of_members
    
    shares = []
    for i in range(number_of_members):
        share_cents = base_cents
        if i < remainder_cents:
            share_cents += 1
        shares.append(Decimal(share_cents) / Decimal("100"))
        
    return shares
