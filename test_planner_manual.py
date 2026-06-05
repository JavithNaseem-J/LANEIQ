import json
import logging
import sys

logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, "f:/DSML/LANEIQ")

from src.agents.planner import planner_node

BRIEFS = [
    "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026. Prefer air freight.",
    "We need to move 2000 kg of textiles from NSICT Mumbai to Abu Dhabi. Deadline is July 5, 2026.",
    "Urgent: 150 kg of perishables from Delhi ICD to Jebel Ali, must arrive by June 10, 2026.",
    "Send 3500 kg of industrial machinery from Chennai to Jebel Ali via sea. Deadline Aug 1, 2026.",
    "Road shipment of 800 kg chemicals from Abu Dhabi to NSICT Mumbai, needed by June 30, 2026.",
]

for idx, brief in enumerate(BRIEFS, 1):
    state = {"shipment_brief": brief, "decomposed_tasks": [], "error": None}
    result = planner_node(state)
    print(f"Brief {idx}: {brief[:65]}...")
    if result.get("error"):
        print(f"  ERROR: {result['error']}")
    else:
        print(f"  Extracted: {json.dumps(result['decomposed_tasks'][0], indent=2)}")
    print()
