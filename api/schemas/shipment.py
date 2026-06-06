from pydantic import BaseModel, Field, field_validator


class ShipmentRequest(BaseModel):
    shipment_brief: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Free-text description of the shipment",
        examples=["Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026."],
    )

    @field_validator("shipment_brief")
    @classmethod
    def brief_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("shipment_brief must not be blank")
        return v.strip()
