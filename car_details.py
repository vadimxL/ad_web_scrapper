from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Any, Optional


@dataclass
class CarDetails:
    # Fields without default values
    id: int
    car_model: str
    year: int
    current_price: float
    date_added_epoch: int
    date_added: str
    feed_source: str

    # Fields with default values
    city: str = 'N/A'
    manufacturer_he: str = 'N/A'
    hp: Optional[int] = None
    hand: Optional[int] = None
    kilometers: Optional[int] = None
    prices: List[Dict[str, Any]] = field(default_factory=list)
    blind_spot: Optional[bool] = None
    smart_cruise_control: Optional[bool] = None
    manuf_en: str = 'N/A'
    updated_at: Optional[str] = None
    gear_type: str = 'N/A'


def create_car_details(feed_item: Dict[str, Any], row2_without_hp: str, horsepower_value: Optional[int],
                       hand: Optional[int], mileage_numeric: Optional[int], price_numeric: float,
                       date_added_epoch: int, formatted_date: str, blind_spot: Optional[bool],
                       smart_cruise_control: Optional[bool]) -> CarDetails:
    # Create and return an instance of CarDetails
    car_details = CarDetails(
        id=feed_item['id'],
        car_model=f"{feed_item['model']} {row2_without_hp}",
        year=feed_item['year'],
        current_price=price_numeric,
        date_added_epoch=date_added_epoch,
        date_added=formatted_date,
        feed_source=feed_item['feed_source'],

        # Fields with default values
        city=feed_item.get('city', 'N/A'),
        manufacturer_he=feed_item.get('manufacturer', 'N/A'),
        hp=horsepower_value,
        hand=hand,
        kilometers=mileage_numeric,
        prices=[{'price': price_numeric, 'date': date.today().strftime("%d/%m/%Y")}],
        blind_spot=blind_spot,
        smart_cruise_control=smart_cruise_control,
        manuf_en=feed_item.get('manufacturer_eng', 'N/A'),
        updated_at=feed_item.get('updated_at')
    )

    return car_details


# Example usage of the function
# You would call the function with appropriate arguments
# Assuming you have feed_item and other necessary variables defined:
# car_details_instance = create_car_details(
#     feed_item=feed_item,
#     row2_without_hp="row2_without_hp_value",
#     horsepower_value=100,
#     hand=2,
#     mileage_numeric=50000,
#     price_numeric=15000.0,
#     date_added_epoch=1625184000,
#     formatted_date="02/07/2021",
#     blind_spot=True,
#     smart_cruise_control=False
# )

# Now you can access the attributes of the data class instance using dot notation:
# e.g., print(car_details_instance.city)
