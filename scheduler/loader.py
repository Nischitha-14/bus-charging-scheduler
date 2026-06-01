"""
Loads scenario data from JSON files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List
from .models import Bus, ScenarioData


def parse_time(time_str: str, date_str: str = "2025-06-15") -> datetime:
    """Parse time string like '19:00' into datetime"""
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")


def load_scenario(json_path: Path) -> ScenarioData:
    """
    Load a scenario from JSON file.
    Expected JSON structure:
    {
        "name": "Scenario 1",
        "weights": {
            "individual": 1.0,
            "operator": 1.0,
            "overall": 1.0
        },
        "buses": {
            "BK": [
                {"id": "bus-BK-01", "company": "kpn", "start_time": "19:00"},
                ...
            ],
            "KB": [
                {"id": "bus-KB-01", "company": "freshbus", "start_time": "19:00"},
                ...
            ]
        }
    }
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    buses = []

    # Parse BK direction buses
    if 'buses' in data and 'BK' in data['buses']:
        for bus_data in data['buses']['BK']:
            bus = Bus(
                id=bus_data['id'],
                company=bus_data['company'],
                direction='BK',
                start_time=parse_time(bus_data['start_time']),
            )
            buses.append(bus)

    # Parse KB direction buses
    if 'buses' in data and 'KB' in data['buses']:
        for bus_data in data['buses']['KB']:
            bus = Bus(
                id=bus_data['id'],
                company=bus_data['company'],
                direction='KB',
                start_time=parse_time(bus_data['start_time']),
            )
            buses.append(bus)

    scenario = ScenarioData(
        name=data.get('name', 'Unnamed Scenario'),
        buses=buses,
        weights=data.get('weights', {'individual': 1.0, 'operator': 1.0, 'overall': 1.0}),
    )

    return scenario


def load_all_scenarios(scenarios_dir: Path) -> List[ScenarioData]:
    """Load all scenario JSON files from directory"""
    scenarios = []
    json_files = sorted(scenarios_dir.glob('scenario_*.json'))

    for json_file in json_files:
        scenario = load_scenario(json_file)
        scenarios.append(scenario)

    return scenarios
