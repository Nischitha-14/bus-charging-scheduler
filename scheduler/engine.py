"""
Scheduling engine: assigns buses to charging stations and resolves conflicts.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from .models import Bus, BusJourney, ChargeEvent, Schedule, ScenarioData
from . import rules


# Route distances in km from start
ROUTE_BK = {
    'Bengaluru': 0,
    'A': 100,
    'B': 220,
    'C': 320,
    'D': 440,
    'Kochi': 540,
}

ROUTE_KB = {
    'Kochi': 0,
    'D': 100,
    'C': 220,
    'B': 320,
    'A': 440,
    'Bengaluru': 540,
}

# Constants
BATTERY_RANGE = 240  # km
CHARGE_TIME = 25  # minutes
SPEED = 60  # km/h
CHARGERS = ['A', 'B', 'C', 'D']


def get_route(direction: str) -> Dict[str, float]:
    """Get route (station → km) for direction"""
    return ROUTE_BK if direction == 'BK' else ROUTE_KB


def get_feasible_patterns(direction: str) -> List[List[str]]:
    """
    Generate all feasible charging patterns for a direction.
    Feasible = at least one from first half, at least one from second half.
    For BK: first half {A, B}, second half {C, D}
    For KB: first half {D, C}, second half {B, A}
    """
    if direction == 'BK':
        first_half = ['A', 'B']
        second_half = ['C', 'D']
    else:  # KB
        first_half = ['D', 'C']
        second_half = ['B', 'A']

    patterns = []

    # All non-empty subsets of first half × all non-empty subsets of second half
    for mask1 in range(1, 2 ** len(first_half)):  # at least one from first half
        for mask2 in range(1, 2 ** len(second_half)):  # at least one from second half
            first = [first_half[i] for i in range(len(first_half)) if mask1 & (1 << i)]
            second = [second_half[i] for i in range(len(second_half)) if mask2 & (1 << i)]
            pattern = sorted(first + second)
            if pattern not in patterns:
                patterns.append(pattern)

    return patterns


def is_pattern_feasible(pattern: List[str], direction: str) -> bool:
    """
    Check if charging pattern is feasible:
    never exceeds BATTERY_RANGE between consecutive charge points.
    """
    route = get_route(direction)
    start_km = 0
    end_km = 540

    # Build checkpoint sequence: start → stations in pattern → end
    checkpoints = [start_km] + [route[station] for station in pattern] + [end_km]

    # Check each segment
    for i in range(len(checkpoints) - 1):
        segment_km = checkpoints[i + 1] - checkpoints[i]
        if segment_km > BATTERY_RANGE:
            return False

    return True


def simulate_journey(
    bus: Bus,
    pattern: List[str],
    charger_availability: Dict[str, datetime],
) -> BusJourney:
    """
    Simulate bus journey with charging pattern.
    Updates charger_availability to reflect when each charger is next available.
    """
    route = get_route(bus.direction)
    journey = BusJourney(bus=bus, charge_stations=pattern)

    current_time = bus.start_time
    current_km = 0

    # Travel to each charging station and charge
    for station in pattern:
        station_km = route[station]
        travel_km = station_km - current_km

        # Calculate travel time
        travel_minutes = (travel_km / SPEED) * 60
        arrival_time = current_time + timedelta(minutes=travel_minutes)

        # Check charger availability
        charger_available = charger_availability.get(station, bus.start_time)
        wait_minutes = max(0, (charger_available - arrival_time).total_seconds() / 60)

        charge_start = max(arrival_time, charger_available)
        charge_end = charge_start + timedelta(minutes=CHARGE_TIME)

        # Record charge event
        event = ChargeEvent(
            bus_id=bus.id,
            station=station,
            arrival_time=arrival_time,
            wait_minutes=wait_minutes,
            charge_start=charge_start,
            charge_end=charge_end,
        )
        journey.charge_events.append(event)

        # Update charger availability
        charger_availability[station] = charge_end

        current_time = charge_end
        current_km = station_km

    # Travel to final destination
    final_km = route['Kochi'] if bus.direction == 'BK' else route['Bengaluru']
    travel_km = final_km - current_km
    travel_minutes = (travel_km / SPEED) * 60
    journey.arrival_time = current_time + timedelta(minutes=travel_minutes)

    return journey


def schedule_scenario(scenario: ScenarioData) -> Schedule:
    """
    Schedule all buses in a scenario.
    Returns a Schedule with computed scores based on scenario weights.
    """
    # Track charger availability
    charger_availability: Dict[str, datetime] = {}

    # Sort buses by start time
    sorted_buses = sorted(scenario.buses, key=lambda b: b.start_time)

    journeys = []

    # Assign each bus to a charging pattern and simulate
    for bus in sorted_buses:
        feasible_patterns = get_feasible_patterns(bus.direction)
        feasible_patterns = [p for p in feasible_patterns if is_pattern_feasible(p, bus.direction)]

        # Greedy: pick the first feasible pattern (could be optimized)
        if feasible_patterns:
            pattern = feasible_patterns[0]
        else:
            pattern = []

        journey = simulate_journey(bus, pattern, charger_availability)
        journeys.append(journey)

    # Calculate scores using the rules
    schedule = Schedule(journeys=journeys, scores={}, total_score=0.0)

    # Compute each rule's score
    scores = {}
    for rule_name, rule_func in rules.RULES.items():
        scores[rule_name] = rule_func(schedule)

    # Compute weighted total score
    total_score = sum(
        scores.get(name, 0.0) * scenario.weights.get(name, 1.0)
        for name in scenario.weights
    )

    schedule.scores = scores
    schedule.total_score = total_score

    return schedule
