import json
import time
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from src.features.transform import PORT_COORDS, haversine

_STRATEGY_MAP = {
    "AUTOMATIC": routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
    "PATH_CHEAPEST_ARC": routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
    "SAVINGS": routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
    "PARALLEL_CHEAPEST_INSERTION": routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
}

_BEST_CONFIG_PATH = repo_root / "models" / "solver_configs" / "best_config.json"


def load_best_config():
    """Load solver config from best_config.json. Falls back to defaults if missing."""
    if _BEST_CONFIG_PATH.exists():
        with open(_BEST_CONFIG_PATH) as f:
            cfg = json.load(f)
        return {
            "strategy": _STRATEGY_MAP.get(
                cfg.get("strategy", "PARALLEL_CHEAPEST_INSERTION"),
                routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
            ),
            "time_limit": cfg.get("time_limit", 30),
            "vehicle_capacity_kg": cfg.get("vehicle_capacity_kg", 6000),
            "num_vehicles": cfg.get("num_vehicles", 15),
            "truck_cost_per_km": cfg.get("truck_cost_per_km", 1.50),
        }
    # Sensible fallback when no config file exists
    return {
        "strategy": routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
        "time_limit": 30,
        "vehicle_capacity_kg": 6000,
        "num_vehicles": 15,
        "truck_cost_per_km": 1.50,
    }


def create_data_model(inputs, config=None):
    data = {}
    nodes = [{"port": "Jebel Ali", "type": "depot", "id": 0}]
    demands = [0]
    time_windows = [(0, 1000000)]
    pickups_deliveries = []

    node_idx = 1
    for i, m in enumerate(inputs):
        nodes.append({"port": m["origin"], "type": "pickup", "shipment": m, "id": node_idx})
        demands.append(int(m["weight_kg"]))
        ready = m["time_window"]["ready_hours"]
        deadline = m["time_window"]["deadline_hours"]
        time_windows.append((ready, deadline))
        node_idx += 1

    for i, m in enumerate(inputs):
        nodes.append({"port": m["destination"], "type": "delivery", "shipment": m, "id": node_idx})
        demands.append(-int(m["weight_kg"]))
        ready = m["time_window"]["ready_hours"]
        deadline = m["time_window"]["deadline_hours"]
        time_windows.append((ready, deadline))
        node_idx += 1

    n_shipments = len(inputs)
    for i in range(n_shipments):
        pickups_deliveries.append([i + 1, i + 1 + n_shipments])

    data["nodes"] = nodes
    data["demands"] = demands
    data["time_windows"] = time_windows
    data["pickups_deliveries"] = pickups_deliveries

    n_nodes = len(nodes)
    dist_matrix = [[0] * n_nodes for _ in range(n_nodes)]
    for i in range(n_nodes):
        for j in range(n_nodes):
            if i != j:
                p1 = nodes[i]["port"]
                p2 = nodes[j]["port"]
                dist = haversine(PORT_COORDS[p1][0], PORT_COORDS[p1][1], PORT_COORDS[p2][0], PORT_COORDS[p2][1])
                dist_matrix[i][j] = int(dist)

    data["distance_matrix"] = dist_matrix
    cfg = config or load_best_config()
    data["num_vehicles"] = cfg.get("num_vehicles", 15)
    data["vehicle_capacities"] = [cfg.get("vehicle_capacity_kg", 6000)] * data["num_vehicles"]
    data["depot"] = 0
    return data


def solve(inputs, config=None):
    cfg = config or load_best_config()
    start_time = time.time()
    data = create_data_model(inputs, config=cfg)

    manager = pywrapcp.RoutingIndexManager(len(data["distance_matrix"]), data["num_vehicles"], data["depot"])
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        return data["distance_matrix"][manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        return data["demands"][manager.IndexToNode(from_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, data["vehicle_capacities"], True, "Capacity")

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        dist = data["distance_matrix"][from_node][to_node]
        return int(dist / 50.0)  # Assumed speed 50 km/h

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(time_callback_index, 1000000, 1000000, False, "Time")
    time_dimension = routing.GetDimensionOrDie("Time")

    for node, tw in enumerate(data["time_windows"]):
        index = manager.NodeToIndex(node)
        time_dimension.CumulVar(index).SetRange(tw[0], tw[1])

    for i in range(data["num_vehicles"]):
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.Start(i)))
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))

    for request in data["pickups_deliveries"]:
        pickup_index = manager.NodeToIndex(request[0])
        delivery_index = manager.NodeToIndex(request[1])
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index))
        routing.solver().Add(time_dimension.CumulVar(pickup_index) <= time_dimension.CumulVar(delivery_index))

    # Allow dropping nodes with a penalty
    penalty = 1000000
    for node in range(1, len(data["distance_matrix"])):
        routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = cfg.get(
        "strategy",
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
    )
    search_parameters.time_limit.seconds = cfg.get("time_limit", 30)

    solution = routing.SolveWithParameters(search_parameters)

    comp_time = time.time() - start_time
    routes = []
    total_distance = 0
    dropped_nodes = []

    if solution:
        for node in range(1, len(data["distance_matrix"])):
            if solution.Value(routing.NextVar(manager.NodeToIndex(node))) == manager.NodeToIndex(node):
                dropped_nodes.append(node)

        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            if routing.IsEnd(solution.Value(routing.NextVar(index))):
                continue

            route_distance = 0
            route_shipments = []

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                if node_index != 0 and data["nodes"][node_index]["type"] == "pickup":
                    route_shipments.append(data["nodes"][node_index]["shipment"]["shipment_id"])

                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)

            routes.append({"vehicle_id": vehicle_id, "distance_km": route_distance, "shipments": route_shipments})
            total_distance += route_distance

    # Cost per km comes from loaded config
    truck_cost_per_km = cfg.get("truck_cost_per_km", 1.50)
    total_cost = total_distance * truck_cost_per_km

    return {
        "routes": routes,
        "total_distance": total_distance,
        "total_cost": total_cost,
        "computation_time": comp_time,
        "dropped_nodes": dropped_nodes,
    }


if __name__ == "__main__":
    input_path = repo_root / "data" / "features" / "routing_inputs.json"
    with open(input_path, "r") as f:
        data_inputs = json.load(f)

    res = solve(data_inputs[:50])
    print("VRP Total Distance:", res["total_distance"])
    print("VRP Total Cost ($):", res["total_cost"])
    print("VRP Comp Time:", res["computation_time"])
