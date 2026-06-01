"""
Pluggable scoring rules for bus schedules.
Each rule returns a raw score; lower is better.
Weights multiply the scores to compute total_score.
"""

from .models import Schedule
from typing import Dict
import statistics


def rule_individual(schedule: Schedule) -> float:
    """
    Individual rule: minimize maximum wait time any single bus experiences.
    Score = maximum wait time in minutes across all buses.
    """
    max_wait = 0.0
    for journey in schedule.journeys:
        for event in journey.charge_events:
            max_wait = max(max_wait, event.wait_minutes)
    return max_wait


def rule_operator(schedule: Schedule) -> float:
    """
    Operator rule: minimize variance in wait times per operator/company.
    Penalizes scenarios where some operators' buses wait much longer than others.
    Score = average variance of wait times per company.
    """
    company_waits: Dict[str, list] = {}

    for journey in schedule.journeys:
        company = journey.bus.company
        if company not in company_waits:
            company_waits[company] = []

        for event in journey.charge_events:
            company_waits[company].append(event.wait_minutes)

    # Calculate variance for each company
    variances = []
    for company, waits in company_waits.items():
        if len(waits) > 1:
            variances.append(statistics.variance(waits))
        elif len(waits) == 1:
            variances.append(0.0)

    return sum(variances) / len(variances) if variances else 0.0


def rule_overall(schedule: Schedule) -> float:
    """
    Overall rule: minimize total network time.
    Score = sum of delays (arrival_time - start_time) for all buses in minutes.
    """
    total_delay_minutes = 0.0
    for journey in schedule.journeys:
        delay = (journey.arrival_time - journey.bus.start_time).total_seconds() / 60
        total_delay_minutes += delay
    return total_delay_minutes


# Registry of available rules - add new rules here
RULES = {
    'individual': rule_individual,
    'operator': rule_operator,
    'overall': rule_overall,
}
