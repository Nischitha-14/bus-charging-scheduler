# Bus Charging Scheduler

A system for scheduling electric bus charging at shared stations on the Bengaluru-Kochi corridor.

## Problem

Electric buses travel a 540 km route: Bengaluru → A → B → C → D → Kochi
- Segment distances: 100, 120, 100, 120, 100 km
- Battery range: 240 km (charges to full in 25 min)
- Speed: 60 km/h
- 1 charger per station (A, B, C, D only)
- 20 buses per scenario (10 each direction)
- **Hard constraint**: Never exceed 240 km between charges
- **Soft constraints** (weighted):
  - Individual: minimize max wait time for any bus
  - Operator: minimize variance in wait times per operator
  - Overall: minimize total network delays

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## Project Structure

```
bus-charging-scheduler/
├── app.py                    # Streamlit UI
├── scheduler/
│   ├── __init__.py
│   ├── models.py             # Data structures
│   ├── rules.py              # Scoring functions
│   ├── engine.py             # Scheduling algorithm
│   └── loader.py             # JSON scenario loader
├── scenarios/
│   ├── scenario_1.json       # Even spacing
│   ├── scenario_2.json       # Bunched start
│   ├── scenario_3.json       # Asymmetric load
│   ├── scenario_4.json       # Operator-heavy weights
│   └── scenario_5.json       # Worst case
├── requirements.txt
└── README.md
```

## Scenarios

**Scenario 1**: Even 15-minute spacing, balanced weights (1.0, 1.0, 1.0)

**Scenario 2**: Bunched arrivals (8-minute intervals), balanced weights

**Scenario 3**: Asymmetric load (10 BK vs 4 KB buses), balanced weights

**Scenario 4**: Heavy operator weighting (2.0), cluster of same-operator buses

**Scenario 5**: Worst case - continuous 8-minute bunching for 80 minutes

## Usage

1. **Select a scenario** from the dropdown
2. **View input data** - all buses departing in that scenario
3. **Check scores**:
   - Individual: Max wait time (minutes)
   - Operator: Variance in waits per company
   - Overall: Total delay (minutes)
4. **Review per-bus timetable** - arrival, wait, charge times, final arrival
5. **Check station queues** - order of buses at each charger

## Scheduling Algorithm

1. **Pre-compute feasible patterns**: For each direction, enumerate all valid charging station combinations
   - BK direction: at least one from {A, B}, at least one from {C, D}
   - KB direction: at least one from {D, C}, at least one from {B, A}
   
2. **Assign buses greedily**: Sort by start time, assign each to first feasible pattern

3. **Simulate timeline**: 
   - Each bus travels, stopping at assigned chargers
   - Chargers service buses FIFO (one at a time, 25 min each)
   - Calculate arrival, wait time, charge period

4. **Score the schedule**: Using weighted sum of three rules:
   ```
   total_score = (individual_score * individual_weight) +
                 (operator_score * operator_weight) +
                 (overall_score * overall_weight)
   ```

## Data Structures

### Bus
```python
id: str                    # "bus-BK-01"
company: str               # "kpn", "freshbus", "flixbus"
direction: str             # "BK" or "KB"
start_time: datetime       # departure time from origin
```

### BusJourney
```python
bus: Bus
charge_stations: List[str]  # ["A", "C"] or ["B", "D"] etc.
charge_events: List[ChargeEvent]
arrival_time: datetime      # at final destination
```

### ChargeEvent
```python
bus_id: str
station: str
arrival_time: datetime      # when bus reaches station
wait_minutes: float         # time waiting for charger
charge_start: datetime      # when charging begins
charge_end: datetime        # when charging completes
```

## Changing Weights

To change rule weights for a scenario, edit the JSON scenario file:

```json
{
  "name": "My Scenario",
  "weights": {
    "individual": 2.0,    # Prioritize fair wait times
    "operator": 0.5,      # Less concern for operator variance
    "overall": 1.0        # Standard network efficiency
  },
  "buses": { ... }
}
```

The weights are **not hardcoded** - all weighting happens at runtime from the scenario JSON.

## Adding a New Rule

1. **Add scoring function** to `scheduler/rules.py`:
```python
def rule_fairness(schedule: Schedule) -> float:
    """Your new rule description"""
    score = 0.0
    for journey in schedule.journeys:
        # Calculate some metric
        score += calculation
    return score / len(schedule.journeys)
```

2. **Register in RULES dict** at bottom of `rules.py`:
```python
RULES = {
    'individual': rule_individual,
    'operator': rule_operator,
    'overall': rule_overall,
    'fairness': rule_fairness,  # ← Add here
}
```

3. **Add weight to scenario JSON**:
```json
{
  "weights": {
    "individual": 1.0,
    "operator": 1.0,
    "overall": 1.0,
    "fairness": 1.5
  }
}
```

**No changes needed to the engine** - it automatically picks up new rules via the RULES registry.

## Assumptions

1. **All buses start with full battery** (240 km range)
2. **Chargers are identical**, rate-limited to one bus per station at a time
3. **Charge time is fixed** at 25 minutes regardless of charge level
4. **No driver shifts, breaks, or rest periods** considered
5. **Single charger per station** (no multi-charger stations)
6. **Routes are fixed** - buses always follow Bengaluru→A→B→C→D→Kochi
7. **Buses can only charge at designated stations** (A, B, C, D)
8. **No dynamic rerouting** - charging pattern decided upfront, not in real-time
9. **Timestamps are all on the same day** (2025-06-15)
10. **Bidirectional traffic** (BK and KB) share the same physical chargers

## Future Extensions

The design supports these without code changes (via data only):

- **Multiple chargers per station**: Add `station_chargers` dict to scenario
- **New stations**: Modified route dict in engine
- **Priority buses**: Add `priority` field to Bus, use in scheduling heuristic
- **Variable charge times**: Add `charge_time_map` to scenario
- **Electricity costs**: Add cost rule to `rules.py` and weight in scenario JSON
- **Driver shifts**: Add `max_shift_hours` to Bus, check in engine
- **Multiple routes**: Parameterize route dict, load from scenario

See `ARCHITECTURE.md` for detailed design rationale.
