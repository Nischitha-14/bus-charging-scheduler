from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class Bus:
    """Represents an electric bus in the network"""
    id: str
    company: str  # 'kpn', 'freshbus', 'flixbus'
    direction: str  # 'BK' (Bengaluru→Kochi) or 'KB' (Kochi→Bengaluru)
    start_time: datetime


@dataclass
class ChargeEvent:
    """Records a charging event for a bus at a station"""
    bus_id: str
    station: str
    arrival_time: datetime
    wait_minutes: float
    charge_start: datetime
    charge_end: datetime


@dataclass
class BusJourney:
    """Complete journey timeline for a single bus"""
    bus: Bus
    charge_stations: List[str]  # stations where this bus charges
    charge_events: List[ChargeEvent] = field(default_factory=list)
    arrival_time: datetime = None  # arrival at final destination


@dataclass
class ScenarioData:
    """Represents a charging scenario with buses and rules"""
    name: str
    buses: List[Bus]
    weights: Dict[str, float]  # {'individual': float, 'operator': float, 'overall': float}


@dataclass
class Schedule:
    """Complete schedule for all buses in a scenario"""
    journeys: List[BusJourney]
    scores: Dict[str, float]  # individual, operator, overall scores
    total_score: float
