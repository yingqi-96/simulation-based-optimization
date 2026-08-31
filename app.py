import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from engine import t1_data_check, t1_run_hybrid_analysis, t2_data_check, all_scenarios, t2_run_hybrid_analysis, t2_run_resource_optimizer
from simulation import run_simulation
from config import CONFIG
from ui_components.display_results import display_stress_test_results, display_optimizer_results

# 1. Initialize session keys with safe defaults
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "none" # Default state

if "ran_sim" not in st.session_state:
    st.session_state.ran_sim = False

# --- WORLD SETTINGS (Global) ---
with st.sidebar:
    st.title("🌍 Factory Settings")

    # Financials
    st.subheader("Financials")
    st.number_input("Part Revenue ($)", 10, 5000, 150, key="global_rev")
    st.number_input("Machine Cost ($/day)", 10, 5000, 500, key="global_m_cost")
    st.number_input("Worker Wage ($/hr)", 5, 500, 10, key="global_w_cost")
    st.number_input("Shift Length (hours)", 1, 24, 8, key="global_shift")
    
    st.divider()
    
    # Physics
    st.subheader("Production")
    # Using a Range Slider as discussed - returns a tuple (min, max)
    p_range = st.slider(
        "Process Time (mins)", 
        min_value=1, max_value=60, value=(8, 30), 
        key="global_p_range"
    )

    # st.divider()
    # st.subheader("🛠️ Session State Debugger")
    # # Create a sorted copy of the state
    # ordered_state = dict(sorted(st.session_state.items()))

    # st.write(ordered_state)

# --- MAIN INTERFACE ---
st.title("🎮 AI-Driven Factory Sandbox")
tab1, tab2, tab3 = st.tabs(["📖 Introduction", "🚀 Capacity Stress Test", "🤖 Resource Optimizer"])

# --- TAB 1: Introduction ---
with tab1:
    st.subheader("Welcome to the AI-Driven Factory Sandbox! 🎮")
    st.markdown("""
    This is a **personal project** exploring the intersection of **Artificial Intelligence and Industrial Simulation**. 
    It serves as a **proof of concept** for using Genetic Algorithm to define production line configurations.

    **Overview:**
    This interactive tool allows you to explore how different factory configurations perform under various demand scenarios. 
    Whether you're looking to find the maximum throughput of a given setup or optimize your resources for a specific demand target, this sandbox has got you covered.

    **How to Use:**
    1.  Input your desired Factory parameters in the sidebar (e.g., shift length, part revenue, machine cost).
    2.  Navigate to the tabs above to select your simulation scenario.
    3. Run the simulations and watch as the AI optimizes your factory configuration in real-time!
    
""")

# --- TAB 2: Maximum Demand ---
with tab2:
    st.subheader("What is our maximum capacity?")
    st.info("""
        * **Goal:** Fix your resources (Machines/Workers) to find the maximum demand throughput.
        * **Constraint:** Assumes a 1:1 Machine-to-Worker ratio.
        * **Logic:** The AI will "push" the arrival rate until the queue becomes unstable.
    """)    

    # 1. User Inputs
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Number of Machines", 1, 20, 5, key="t1_m")
    with col2:
        st.number_input("Number of Workers", 1, 20, 3, key="t1_w")
    
    sla_limit = st.slider("Max Acceptable Lead Time (mins)", 10, 200, 60, key="t1_lead_time_limit")

    if st.button("Calculate Saturation Point", type="secondary"):
        # 2. Gather Simulation Settings
        config = {
            "mode": "stress_test",
            "t1_m": st.session_state.t1_m,
            "t1_w": st.session_state.t1_w,
            "t1_lead_time_limit": st.session_state.t1_lead_time_limit,
            "p_min": st.session_state.global_p_range[0],
            "p_max": st.session_state.global_p_range[1],
            "shift_length": st.session_state.global_shift,
            "part_revenue": st.session_state.global_rev,
            "machine_cost": st.session_state.global_m_cost,
            "worker_wage": st.session_state.global_w_cost
        }

        # 3. Run AI engine
        with st.status("🚀 Running Stress Test...", expanded=True) as status:
            st.write("Step 1: Running Data Check...")
            # This ensures config is complete (your t1_data_check function)
            vetted_config = t1_data_check(config)

            st.write("Step 2: GA Scout finding the breaking point...")
            # Run the hybrid analysis (Scout -> then Sweep)
            sweep_data, scouted_limit, ga_instance = t1_run_hybrid_analysis(vetted_config)
            
            status.update(label="✅ Stress Test Complete!", state="complete")
        
        # 4. Store results in Session State for the "Victory Screen"
        st.session_state.t1_config_ran_sim = True
        st.session_state.config_current_mode = "stress_test"
        st.session_state.t1_sweep_results = sweep_data
        st.session_state.t1_limit_found = scouted_limit
        st.session_state.t1_ga_instance = ga_instance

        st.rerun()

    if st.session_state.get("t1_config_ran_sim"):
        display_stress_test_results(st.session_state)     

# --- TAB 3: Required Resources ---
def update_from_interval():
    """Calculates Daily Output from Interval (Integer Only)."""
    current_interval = st.session_state.t2_arr
    
    if current_interval > 0:
        shift_length_mins = st.session_state.global_shift * 60
        # How many full 5-minute blocks fit in the shift?
        daily_goal = shift_length_mins // current_interval
        st.session_state.t2_daily = int(daily_goal)

def update_from_daily():
    """Calculates Arrival Interval from Daily Output (Integer Only)."""
    daily_target = int(st.session_state.t2_daily)
    
    if daily_target > 0:
        shift_length_mins = st.session_state.global_shift * 60
        calculated_interval = float(shift_length_mins / daily_target)
        
        # Guard against 0 to prevent SimPy crashes
        st.session_state.t2_arr = max(1.0, calculated_interval)

with tab3:
    st.subheader("What setup do I need to meet this demand target?")
    st.info("""
        * **Goal:** Find the optimal number of Machines and Workers required to handle a specific arrival rate.
        * **Constraint:** Assumes a 1:1 Machine-to-Worker ratio.
        * **Logic:** The AI will "evolve" different factory configurations to find the lowest-cost setup that prevents bottlenecks to meet the demand.
    """)

    # 1. User Inputs
    st.write("#### 🎯 Demand Target")
    st.caption("⚠️ **Note:** The simulated arrival interval will run at **80% (0.8x)** of the selected value to ensure the system is under enough pressure to prevent resource starvation.")

    col1, col2 = st.columns([1, 2])
    simulation_duration = st.session_state.global_shift * 60
    min_daily = 10
    max_daily = int(simulation_duration/1.0)

    with col1:
        # This metric updates instantly as the user moves the slider
        st.number_input("Daily Goal (Parts)", min_daily, max_daily, 96, key="t2_daily", on_change=update_from_daily)

    with col2:
        st.slider("Arrival Interval (min/part)", 1.0, float(simulation_duration / min_daily), 5.0, key="t2_arr", on_change=update_from_interval)
        
    if st.button("Run AI Resource Optimizer", type="secondary"):
        st.session_state.current_mode = "optimizer"

        # 2. Gather Simulation Settings
        config = {
            "mode": "optimizer",
            "t2_arr": st.session_state.t2_arr,
            "t2_daily": st.session_state.t2_daily,
            "p_min": st.session_state.global_p_range[0],
            "p_max": st.session_state.global_p_range[1],
            "shift_length": st.session_state.global_shift,
            "part_revenue": st.session_state.global_rev,
            "machine_cost": st.session_state.global_m_cost,
            "worker_wage": st.session_state.global_w_cost
        }

        # 3. Run AI engine
        with st.status("🚀 Running Resource Optimization...", expanded=True) as status:
            st.write("Step 1: Running Data Check...")
            # This ensures config is complete (your t2_data_check function)
            vetted_config = t2_data_check(config)

            st.write("Step 2: Optimizing machine-worker configuration for target demand...")
            # Run the hybrid analysis (Scout -> then Sweep)
            # solution,ga_instance = t2_run_resource_optimizer(vetted_config)
            sweep_data, ai_m, ai_w, ga_instance = t2_run_hybrid_analysis(vetted_config)
            
            status.update(label="✅ Optimization Complete!", state="complete")
        
        # 4. Store results in Session State for the "Victory Screen"
        st.session_state.t2_config_ran_sim = True
        st.session_state.config_current_mode = "optimizer"
        st.session_state.t2_sweep_results = sweep_data
        st.session_state.t2_m = ai_m
        st.session_state.t2_w = ai_w
        st.session_state.t2_ga_instance = ga_instance

        st.rerun()

    if st.session_state.get("t2_config_ran_sim"):
        display_optimizer_results(st.session_state)    