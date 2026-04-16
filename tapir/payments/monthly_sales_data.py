from dataclasses import dataclass
from decimal import Decimal


@dataclass
class MonthlySalesData:
    contract_type_name: str
    sales: Decimal
