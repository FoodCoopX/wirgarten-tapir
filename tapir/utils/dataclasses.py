from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CalculationPart:
    explanation: str
    value: Decimal
