# ── Planner Agent 

PLANNER_SYSTEM_PROMPT = """You are a freight logistics planner for LANEIQ, an AI-powered freight routing system.

Your job is to extract structured shipment details from a free-text shipment brief provided by a user.

You MUST call the `extract_shipment` tool with the extracted fields. Do NOT reply with plain text.

Rules:
- origin and destination must be one of: "NSICT Mumbai", "Chennai", "Abu Dhabi", "Jebel Ali", "Delhi ICD"
- cargo_type must be one of: "Electronics", "Perishables", "Machinery", "Textiles", "Chemicals"
- preferred_mode must be one of: "sea", "air", "road"
- weight_kg must be a positive number
- deadline must be an ISO 8601 date string (YYYY-MM-DD)
- If a field is not mentioned, make a reasonable inference based on context (e.g. heavy machinery defaults to sea)
- If you cannot extract or infer a field with confidence, set it to null
"""

PLANNER_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "extract_shipment",
        "description": (
            "Extract structured shipment details from a free-text brief. "
            "Call this tool with all fields you can extract or infer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin_port": {
                    "type": "string",
                    "enum": ["NSICT Mumbai", "Chennai", "Abu Dhabi", "Jebel Ali", "Delhi ICD"],
                    "description": "Port of origin",
                },
                "destination_port": {
                    "type": "string",
                    "enum": ["NSICT Mumbai", "Chennai", "Abu Dhabi", "Jebel Ali", "Delhi ICD"],
                    "description": "Port of destination",
                },
                "cargo_type": {
                    "type": "string",
                    "enum": ["Electronics", "Perishables", "Machinery", "Textiles", "Chemicals"],
                    "description": "Type of cargo being shipped",
                },
                "cargo_weight_kg": {
                    "type": "number",
                    "description": "Total cargo weight in kilograms",
                },
                "deadline": {
                    "type": "string",
                    "description": "Delivery deadline in ISO 8601 format (YYYY-MM-DD)",
                },
                "preferred_mode": {
                    "type": "string",
                    "enum": ["sea", "air", "road"],
                    "description": "Preferred transport mode",
                },
            },
            "required": [
                "origin_port",
                "destination_port",
                "cargo_type",
                "cargo_weight_kg",
                "deadline",
                "preferred_mode",
            ],
        },
    },
}
