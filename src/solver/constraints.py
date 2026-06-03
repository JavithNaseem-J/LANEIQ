"""
Named search strategy configurations for the OR-Tools VRP solver.
Each config is a dict consumed by vrp.solve() via the `config` parameter.
"""

from ortools.constraint_solver import routing_enums_pb2

STRATEGIES = {
    "AUTOMATIC": {
        "strategy": routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
        "time_limit": 30,
    },
    "PATH_CHEAPEST_ARC": {
        "strategy": routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        "time_limit": 30,
    },
    "SAVINGS": {
        "strategy": routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
        "time_limit": 30,
    },
    "PARALLEL_CHEAPEST_INSERTION": {
        "strategy": routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
        "time_limit": 30,
    },
}

TIME_LIMITS = [10, 30, 60]
