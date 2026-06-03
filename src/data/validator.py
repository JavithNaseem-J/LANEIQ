from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Literal


class ShipmentManifest(BaseModel):
    model_config = ConfigDict(strict=False)

    shipment_id: str
    origin_port: str
    destination_port: str
    cargo_weight_kg: float = Field(gt=0, description="Weight of the cargo in kilograms")
    cargo_type: str
    ready_datetime: datetime
    deadline_datetime: datetime
    preferred_mode: Literal["sea", "air", "road"]
    estimated_value_usd: float = Field(ge=0, description="Estimated value of the cargo in USD")
