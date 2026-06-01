"""
Bus Charging Scheduler - Streamlit UI
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
import pandas as pd

from scheduler import load_all_scenarios, schedule_scenario


def format_time(dt: datetime) -> str:
    """Format datetime as HH:MM"""
    return dt.strftime("%H:%M")


def format_duration(minutes: float) -> str:
    """Format duration in minutes as H:MM"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}:{mins:02d}"


def main():
    st.set_page_config(page_title="Bus Charging Scheduler", layout="wide")
    st.title("🚌 Bus Charging Scheduler")

    # Load scenarios
    scenarios_dir = Path(__file__).parent / "scenarios"
    scenarios = load_all_scenarios(scenarios_dir)

    if not scenarios:
        st.error("No scenarios found in scenarios/ directory")
        return

    # Scenario selector
    scenario_names = [s.name for s in scenarios]
    selected_idx = st.selectbox("Select Scenario", range(len(scenarios)), format_func=lambda i: scenario_names[i])
    selected_scenario = scenarios[selected_idx]

    st.subheader(f"Scenario: {selected_scenario.name}")
    st.write(f"Weights - Individual: {selected_scenario.weights['individual']}, Operator: {selected_scenario.weights['operator']}, Overall: {selected_scenario.weights['overall']}")

    # TAB 1: Input Data
    col1, col2 = st.columns(2)

    with col1:
        st.write("### BK Direction (Bengaluru → Kochi)")
        bk_buses = [b for b in selected_scenario.buses if b.direction == 'BK']
        if bk_buses:
            bk_data = [
                {
                    "Bus ID": b.id,
                    "Company": b.company,
                    "Start Time": format_time(b.start_time),
                }
                for b in sorted(bk_buses, key=lambda x: x.start_time)
            ]
            st.dataframe(pd.DataFrame(bk_data), use_container_width=True)

    with col2:
        st.write("### KB Direction (Kochi → Bengaluru)")
        kb_buses = [b for b in selected_scenario.buses if b.direction == 'KB']
        if kb_buses:
            kb_data = [
                {
                    "Bus ID": b.id,
                    "Company": b.company,
                    "Start Time": format_time(b.start_time),
                }
                for b in sorted(kb_buses, key=lambda x: x.start_time)
            ]
            st.dataframe(pd.DataFrame(kb_data), use_container_width=True)

    # Schedule the scenario
    schedule = schedule_scenario(selected_scenario)

    # TAB 2: Scores
    st.subheader("Schedule Scores")
    score_cols = st.columns(4)
    with score_cols[0]:
        st.metric("Individual (max wait)", f"{schedule.scores.get('individual', 0):.1f} min")
    with score_cols[1]:
        st.metric("Operator (variance)", f"{schedule.scores.get('operator', 0):.1f}")
    with score_cols[2]:
        st.metric("Overall (total delay)", f"{schedule.scores.get('overall', 0):.1f} min")
    with score_cols[3]:
        st.metric("Total Score", f"{schedule.total_score:.1f}")

    # TAB 3: Per-Bus Timetable
    st.subheader("Per-Bus Timetable")

    timetable_data = []
    for journey in sorted(schedule.journeys, key=lambda j: j.bus.start_time):
        stations = ", ".join(journey.charge_stations) if journey.charge_stations else "None"

        # Build charge timeline
        charge_times = []
        for event in journey.charge_events:
            charge_times.append(
                f"{event.station} (arr:{format_time(event.arrival_time)}, wait:{event.wait_minutes:.0f}m, "
                f"chg:{format_time(event.charge_start)}-{format_time(event.charge_end)})"
            )
        charge_timeline = " → ".join(charge_times) if charge_times else "No charging"

        timetable_data.append(
            {
                "Bus ID": journey.bus.id,
                "Company": journey.bus.company,
                "Direction": journey.bus.direction,
                "Start": format_time(journey.bus.start_time),
                "Charge At": stations,
                "Charge Schedule": charge_timeline,
                "Final Arrival": format_time(journey.arrival_time),
                "Total Duration": format_duration((journey.arrival_time - journey.bus.start_time).total_seconds() / 60),
            }
        )

    timetable_df = pd.DataFrame(timetable_data)
    st.dataframe(timetable_df, use_container_width=True)

    # TAB 4: Per-Station View
    st.subheader("Per-Station Charging Queue")

    station_cols = st.columns(4)
    stations = ['A', 'B', 'C', 'D']

    for col, station in zip(station_cols, stations):
        with col:
            st.write(f"#### Station {station}")
            station_queue = []

            for journey in schedule.journeys:
                for event in journey.charge_events:
                    if event.station == station:
                        station_queue.append(event)

            # Sort by charge start time
            station_queue.sort(key=lambda e: e.charge_start)

            if station_queue:
                queue_data = [
                    {
                        "Bus": e.bus_id,
                        "Arrival": format_time(e.arrival_time),
                        "Wait": f"{e.wait_minutes:.0f}m",
                        "Charge": f"{format_time(e.charge_start)}-{format_time(e.charge_end)}",
                    }
                    for e in station_queue
                ]
                st.dataframe(pd.DataFrame(queue_data), use_container_width=True)
            else:
                st.info("No buses charge here")


if __name__ == "__main__":
    main()
