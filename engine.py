import streamlit as st
import pygad
import numpy as np
from simulation import run_simulation
import random
from config import CONFIG


def t1_data_check(config):
    """
    Ensures all required keys exist in config. 
    If missing, it generates values and logs them.
    """    
    # 1. Check for Machine Count (t1_m)
    if "t1_m" not in config or config["t1_m"] is None:
        low, high = CONFIG["range_machines"]
        config["t1_m"] = int(random.uniform(low, high))
        print(f"CHECK: Machine count missing. Assigned: {config['t1_m']}")

    # 2. Check for Worker Count (t1_w)
    if "t1_w" not in config or config["t1_w"] is None:
        low, high = CONFIG["range_workers"]
        config["t1_w"] = int(random.uniform(low, high))
        print(f"CHECK: Worker count missing. Assigned: {config['t1_m']}")

    # 3. Check for SLA / Lead Time Limit (t1_lead_time_limit)
    if "t1_lead_time_limit" not in config:
        config["t1_lead_time_limit"] = CONFIG["lead_time_limit"]
        print(f"CHECK: Lead time limit missing. Assigned: {config['t1_lead_time_limit']}")

    # 4. Check for Process Time Range (p_range)
    if "p_min" not in config:
        config["p_min"] = CONFIG["base_process_time"][0]
        print(f"CHECK: Min process range missing. Assigned: {config['p_min']}")

    if "p_max" not in config:
        config["p_max"] = CONFIG["base_process_time"][1]
        print(f"CHECK: Max process range missing. Assigned: {config['p_max']}")
    
    # 5. Check for Shift Length (shift_length) 
    if "shift_length" not in config:
        config["shift_length"] = CONFIG["shift_length"]
        print(f"CHECK: Shift Length missing. Assigned: {config['shift_length']}")
    
    # 6. Check for Part Revenue (part_revenue) 
    if "part_revenue" not in config:
        config["part_revenue"] = CONFIG["part_revenue"]
        print(f"CHECK: Part Revenue missing. Assigned: {config['part_revenue']}")

    # 7. Check for Machine Cost (machine_cost) 
    if "machine_cost" not in config:
        config["machine_cost"] = CONFIG["machine_cost"]
        print(f"CHECK: Machine Cost missing. Assigned: {config['machine_cost']}")

    # 8. Check for Worker Wage (worker_wage) 
    if "worker_wage" not in config:
        config["worker_wage"] = CONFIG["worker_wage"]
        print(f"CHECK: Worker Wage missing. Assigned: {config['worker_wage']}")

    return config

def t2_data_check(config):
    """
    Ensures all required keys exist in config. 
    If missing, it generates values and logs them.
    """
    # 3. Check for Arrival Rate (t2_arr) 
    if "t2_arr" not in config:
        config["t2_arr"] = CONFIG["arrival_rate"]
        print(f"CHECK: Arrival rate missing. Assigned: {config['t2_arr']}")

    # 4. Check for Process Time Range (p_range)
    if "p_min" not in config:
        config["p_min"] = CONFIG["base_process_time"][0]
        print(f"CHECK: Min process range missing. Assigned: {config['p_min']}")

    if "p_max" not in config:
        config["p_max"] = CONFIG["base_process_time"][1]
        print(f"CHECK: Max process range missing. Assigned: {config['p_max']}")
    
    # 5. Check for Shift Length (shift_length) 
    if "shift_length" not in config:
        config["shift_length"] = CONFIG["shift_length"]
        print(f"CHECK: Shift Length missing. Assigned: {config['shift_length']}")
    
    # 6. Check for Part Revenue (part_revenue) 
    if "part_revenue" not in config:
        config["part_revenue"] = CONFIG["part_revenue"]
        print(f"CHECK: Part Revenue missing. Assigned: {config['part_revenue']}")

    # 7. Check for Machine Cost (machine_cost) 
    if "machine_cost" not in config:
        config["machine_cost"] = CONFIG["machine_cost"]
        print(f"CHECK: Machine Cost missing. Assigned: {config['machine_cost']}")

    # 8. Check for Worker Wage (worker_wage) 
    if "worker_wage" not in config:
        config["worker_wage"] = CONFIG["worker_wage"]
        print(f"CHECK: Worker Wage missing. Assigned: {config['worker_wage']}")

    return config

# Global list to store the AI's "brainstorming" sessions for visualization
all_scenarios = []
simulation_cache = {}

def fitness_func(ga_instance, solution, solution_idx):
    global all_scenarios

    config = ga_instance.custom_config
    mode = config.get("mode")

    # --- MODE: CAPACITY STRESS TEST (TAB 1) ---
    if mode == "stress_test":
        # Initialise variables   
        num_trials = 15  # Run the sim 5 times with DIFFERENT seeds
        avg_lead_times = []
        completed_parts = []
        max_queue_history = []

        # Here, the solution is the 'Arrival Interval' (how fast parts arrive)
        # 1. Get Guess from AI
        target_arrival = round(solution[0], 2)
        config["arrival_rate"] = target_arrival

        # Check if we've scouted this exact spot before
        if target_arrival in simulation_cache:
            data = simulation_cache[target_arrival]

            f_val = data["fitness"]
            p_val = data["avg_parts"]
            l_val = data["avg_lead_time"]
            
            # print(f"CACHE HIT | Testing Arrival: {target_arrival:.2f} | Fitness: {f_val:.2f} | Parts: {p_val:.1f} | Lead Time: {l_val:.2f}")
    
            return f_val
            
        # 2. Run the sim (it will use 't1_m' and 't1_w' automatically)
        for i in range(num_trials):
            # Pass None or a random integer to ensure each trial is unique
            config["seed"] = i
            plant_output = run_simulation(config)
            actual_avg_lead_time = np.mean(plant_output.all_lead_times) if plant_output.all_lead_times else 0
            avg_lead_times.append(actual_avg_lead_time)
            completed_parts.append(plant_output.parts_done)

        # 3. Retrieve values for fitness calculation
        user_sla = config["t1_lead_time_limit"] # Default to 30 mins if not set
        avg_lead_time = sum(avg_lead_times) / num_trials
        avg_parts = int(sum(completed_parts) / num_trials)

        # --- The Fitness Calculation ---
        # 4. Fitness Calculation

        if avg_lead_time > user_sla:
            return 0.1
        
        # Goal 1: Throughput (The "Heavy Lifter")
        parts_score = avg_parts * 1000000 
        
        # Goal 2: Lead Time Efficiency (The "Robustness" Reward)
        # We subtract lead time from 60 to reward SHORTER times
        time_score = (user_sla - avg_lead_time) * 100
                
        fitness = parts_score + time_score

        # base_capacity_score = avg_parts * 1000
        # pressure_bonus = (1 / target_arrival) * 500

        # if actual_avg_lead_time <= user_sla:
        #     # SUCCESS: Full score + Pressure
        #     # Add a precision bonus to reward being close to the limit
        #     precision_bonus = (actual_avg_lead_time / user_sla)**5 * 5000
        #     fitness = base_capacity_score + pressure_bonus + precision_bonus
        # else:
        #     # FAILURE: We use the SAME base score but multiply by closeness.
        #     # This ensures the "drop" isn't a cliff, but a steep slope.
        #     closeness_factor = (user_sla / actual_avg_lead_time) ** 2 # Square it to make the penalty steeper
        #     fitness = (base_capacity_score + pressure_bonus) * closeness_factor
            
        # Store in Cache
        simulation_cache[target_arrival] = {
            "fitness": fitness,
            "avg_parts": avg_parts,
            "avg_lead_time": avg_lead_time
        }
    
        print(f"CACHE NOT HIT | Testing Arrival: {target_arrival:.2f} | Fitness: {fitness:.2f} | Parts: {avg_parts} | Lead Time: {avg_lead_time}")

        return fitness
        
        # Calculate the base throughput value
        # base_capacity_score = parts * 1000
        # pressure_bonus = (1 / target_arrival) * 500
        
        # if actual_avg_lead_time <= user_sla:
        #     # SUCCESS: Full score + Pressure
        #     # Add a precision bonus to reward being close to the limit
        #     precision_bonus = (actual_avg_lead_time / user_sla)**5 * 5000
        #     return base_capacity_score + pressure_bonus + precision_bonus
        # else:
        #     # FAILURE: We use the SAME base score but multiply by closeness.
        #     # This ensures the "drop" isn't a cliff, but a steep slope.
        #     closeness_factor = (user_sla / actual_avg_lead_time) ** 2 # Square it to make the penalty steeper
        #     return (base_capacity_score + pressure_bonus) * closeness_factor
            
    # --- MODE: RESOURCE OPTIMIZER (TAB 2) ---
    elif mode == "optimizer":
        # Initialise variables   
        num_trials = 15  # Run the sim 5 times with DIFFERENT seeds
        avg_lead_times = []
        completed_parts = []
        m_util = []
        w_util = []
        max_queue_history = []

        # --- 1. Extract Resources from the GA's "Guess" ---
        m, w = int(solution[0]), int(solution[1])
        
        # Use a tuple for the cache key since we have multiple variables
        resource_key = (m, w)
        
        if resource_key in simulation_cache:
            return simulation_cache[resource_key]["fitness"]

        # --- 2. Fixed Demand from User Inputs ---
        # We use the target the user selected in the Streamlit slider
        config["arrival_rate"] = config["t2_arr"]*0.8
        config["t2_m"] = m
        config["t2_w"] = w

        for i in range(num_trials):
            config["seed"] = i
            plant_output = run_simulation(config)
            avg_lead_times.append(np.mean(plant_output.all_lead_times) if plant_output.all_lead_times else 0)
            completed_parts.append(plant_output.parts_done)
            m_util.append(plant_output.m_util)
            w_util.append(plant_output.w_util)

        avg_lead_time = sum(avg_lead_times) / num_trials
        avg_parts = sum(completed_parts) / num_trials
        m_util = sum(m_util) / num_trials
        w_util = sum(w_util) / num_trials
        target_demand = config["t2_daily"]
        machine_cost = config["machine_cost"]
        worker_wage = config["worker_wage"]
        shift_length = config["shift_length"]

        # --- 3. The Fitness Calculation (Updated) ---
        if avg_parts < target_demand:
            # FAIL BLOCK: Use a much smaller scale (0 to 1,000,000)
            progress_ratio = avg_parts / target_demand
            fitness = progress_ratio * 1000000
            # Small penalty to encourage adding resources when failing
            fitness -= (m * 100) + (w * 100)

        else:
            # SUCCESS BLOCK: Start at 10,000,000
            # This creates a "Cliff" that the GA must climb to reach success.
            machine_expense = m * machine_cost
            labor_expense = w * worker_wage * shift_length
            total_cost = machine_expense + labor_expense

            # Use a smaller multiplier for cost so it doesn't inflate fitness too much
            cost_merit = (1000000 - total_cost) * 10.0            

            combined_util = (m_util + w_util) / 2 
            util_bonus = combined_util * 100000 

            overproduction_penalty = (avg_parts - target_demand) * 10000
            
            # The 10M floor ensures M:5/W:10 (Success) always beats M:2/W:5 (Fail)
            fitness = 10000000 + cost_merit + util_bonus - overproduction_penalty

        # Store in Cache
        simulation_cache[resource_key] = {
            "fitness": fitness,
            "avg_parts": avg_parts,
            "avg_lead_time": avg_lead_time,
            "avg_m_util": m_util,
            "avg_w_util": w_util
        }

        print(f"CACHE NOT HIT | Testing Machines: {m}, Workers: {w} | Fitness: {fitness:.2f} | Parts: {avg_parts} | Machine Utilization: {m_util:.1f}% | Worker Utilization: {w_util:.1f}%")

        return fitness


# --- MODE: CAPACITY STRESS TEST (TAB 1) ---
def t1_run_ga_scout(config):
    """Fast AI search to find the saturation 'Edge'."""
    global simulation_cache
    simulation_cache = {}

    n_machines = config["t1_m"]
    n_workers = config["t1_w"]
    avg_process_time = (config["p_min"] + config["p_max"])/2

    # 1. Calculate individual capacities
    machine_cap = avg_process_time / n_machines
    worker_cap = avg_process_time / n_workers

    # 2. The Theoretical Limit is the 'Tightest' constraint
    # (The higher the minutes per part, the slower the factory)
    theoretical_limit = max(machine_cap, worker_cap)

    # 3. Set GA search space to be +/- 70% of that limit
    low_bound = max(1.0, theoretical_limit * 0.1) # Don't go below 1 min
    high_bound = theoretical_limit * 5.0

    print(f"DEBUG: low_bound = {low_bound}, high_bound = {high_bound}")
    gene_space = [{"low": low_bound, "high": high_bound, 'step': 0.1}]

    ga_instance = pygad.GA(
        num_generations=50, 
        sol_per_pop=50,
        num_genes=1,
        fitness_func=fitness_func,
        gene_space=gene_space,
        gene_type=float,
        num_parents_mating=25,
        
        # Keep Elitism slightly higher for stability in noisy simulations
        keep_elitism=4,
        
        # TOURNAMENT: Size 3 is a good balance. 
        # Higher numbers make it "greedier" (chooses only the best).
        parent_selection_type="tournament",
        K_tournament=3,

        # MUTATION: The most important part for 1-gene problems
        mutation_type="adaptive",
        mutation_probability=[0.4, 0.1],
        
        # Change to False to allow "creeping" mutations (6.20 -> 6.19)
        mutation_by_replacement=False, 
        
        # Define how far a mutation can "wiggle" from the current value
        # This helps find the exact saturation edge.
        random_mutation_min_val=-0.5, 
        random_mutation_max_val=0.5,

        stop_criteria=["saturate_20"],
        save_best_solutions=True,
        save_solutions=True,
    )
    
    # 4. Run GA
    ga_instance.custom_config = config
    simulation_cache.clear()

    ga_instance.run()

    # 5. Log results for sensitivity analysis
    if ga_instance.generations_completed < 50:
        st.session_state['t1_ga_status'] = {
            "type": "success",
            "msg": f"✅ AI converged early at Generation {ga_instance.generations_completed}!"
        }
    else:
        st.session_state['t1_ga_status'] = {
            "type": "warning",
            "msg": "⚠️ AI reached max generations. Result optimized but may not be 'absolute' peak."
        }

    solution, fitness, idx = ga_instance.best_solution()
    print(f"DEBUG: best_scounted_value = {solution[0]}")

    return round(solution[0], 2), ga_instance


def t1_run_hybrid_analysis(config):
    """
    Uses the GA Scout to find the breaking point, then performs 
    a systematic sweep around that point for charting.
    """
    # --- AI SCOUT ---
    # 1. AI Scouts the limit
    scouted_val, ga_instance = t1_run_ga_scout(config)
    
    # --- SET SWEEP BOUNDARY ---
    # 2. Set Sweep Boundaries around the AI's discovery
    # This shows the immediate impact of small changes in arrival rate
    upper_bound = round(scouted_val * 1.2, 1) # ~7.0 min (Relaxed)
    lower_bound = round(scouted_val * 0.8, 1) # ~4.6 min (Stressed)

    # 3. GENERATE EXTENDED TAILS (Step = 1) ---
    # 3 points above: e.g., 8.0, 9.0, 10.0
    above_range = np.arange(np.ceil(upper_bound), np.ceil(upper_bound) + 5, 1.0)

    # 3 points below: e.g., 3.0, 2.0, 1.0 (Careful! These will likely fail SLA)
    # We use -1.0 as the step to go downwards
    raw_below = np.arange(np.floor(lower_bound), np.floor(lower_bound) - 5, -1.0)
    below_range = np.maximum(0.1, raw_below)

    # 4. Generate 5 test points + AI's scounted value and clean the range
    # Using 7 or 9 points ensures a clean spread
    precision_range = np.linspace(upper_bound, lower_bound, num=5)
    test_range = np.concatenate([above_range, precision_range, below_range, [scouted_val]])
    test_range = np.unique(np.round(test_range, 2))

    # 5. Sort Descending (Slow Arrival -> Fast Arrival)
    test_range = np.sort(test_range)[::-1]

    # --- RUN SWEEP ---
    # 5. intialise sweep data
    sweep_key = "arrival_rate"
    sweep_results = []
    user_sla = config["t1_lead_time_limit"]

    # 6. Run Systematic Sweep
    for val in test_range:
        run_cfg = config.copy()
        run_cfg[sweep_key] = val
        
        plant = run_simulation(run_cfg)
        
        # Calculate final metrics for the table/chart
        actual_avg_lead_time = np.mean(plant.all_lead_times) if plant.all_lead_times else 0
        
        sweep_results.append({
            "arrival_rate": round(val, 2),
            "parts_done": plant.parts_done,
            "max_machine_queue": max(plant.m_queue_history) if plant.m_queue_history else 0,
            "max_worker_queue": max(plant.w_queue_history) if plant.w_queue_history else 0,
            "est_lead_time": round(actual_avg_lead_time, 2),
            "all_records": plant.all_records,
            "within_sla": actual_avg_lead_time <= user_sla,
            "m_util": plant.m_util,
            "w_util": plant.w_util
        })
    
    # print(simulation_cache)

    return sweep_results, scouted_val, ga_instance


# --- MODE: OPTIMIZER (TAB 2) ---
def t2_run_resource_optimizer(config):
    """
    The main entry point for your 'Run Optimization' button in Tab 2.
    """
    # Define Gene space: [Machine (1-100), Workers (1-100)]
    gene_space = [
        {'low': 1, 'high': 50, 'step': 1}, 
        {'low': 1, 'high': 50, 'step': 1}
    ]

    ga_instance = pygad.GA(
        num_generations=50,               # More time to optimize cost after hitting 200
        num_parents_mating=12,            # Slightly more parents for better crossovers
        fitness_func=fitness_func,
        sol_per_pop=50,                   # Broader search for the higher demand target
        num_genes=2,
        gene_space=gene_space,
        gene_type=int,
        parent_selection_type="sss",
        keep_elitism=4,                   # Protect the top 3 configurations
        mutation_percent_genes=20,        # Higher mutation to explore lean boundaries
        mutation_type="random",
        stop_criteria=["saturate_20"],
        save_best_solutions=True,
        save_solutions=True
    )

    # Attach UI metadata to the instance so the fitness function can see it
    ga_instance.custom_config = config
    simulation_cache.clear()

    ga_instance.run()

    # 5. Log results for sensitivity analysis
    if ga_instance.generations_completed < 50:
        st.session_state['t2_ga_status'] = {
            "type": "success",
            "msg": f"✅ AI converged early at Generation {ga_instance.generations_completed}!"
        }
    else:
        st.session_state['t2_ga_status'] = {
            "type": "warning",
            "msg": "⚠️ AI reached max generations. Result optimized but may not be 'absolute' peak."
        }

    solution, fitness, idx = ga_instance.best_solution()
    print(f"DEBUG: best_scounted_value = m: {solution[0]}, w: {solution[1]}")

    return solution, ga_instance


def t2_run_hybrid_analysis(config):
    """
    Uses the GA Scout to find the breaking point, then performs 
    a systematic sweep around that point for charting.
    """
    # --- AI SCOUT ---
    # 1. AI recommended value
    ai_solution, ga_instance = t2_run_resource_optimizer(config)
    ai_m, ai_w = int(ai_solution[0]), int(ai_solution[1])

    # --- SET SWEEP BOUNDARY AND RUN SWEEP ---
    sweep_results = []
    for m in range(ai_m - 2, ai_m + 2): # Test -1 and +1 machine
        for w in range(ai_w - 2, ai_w + 2): # Test -1 and +1 worker
            if m <= 0 or w <= 0:
                continue
            
            run_cfg = config.copy()
            run_cfg["t2_m"] = m
            run_cfg["t2_w"] = w

            plant = run_simulation(run_cfg)

            # Calculate final metrics for the table/chart
            actual_avg_lead_time = np.mean(plant.all_lead_times) if plant.all_lead_times else 0
            
            sweep_results.append({
                "arrival_rate": config["arrival_rate"],
                "daily_target": config["t2_daily"],
                "parts_done": plant.parts_done,
                "max_machine_queue": max(plant.m_queue_history) if plant.m_queue_history else 0,
                "max_worker_queue": max(plant.w_queue_history) if plant.w_queue_history else 0,
                "est_lead_time": round(actual_avg_lead_time, 2),
                "all_records": plant.all_records,
                "target_met" : plant.parts_done >= config["t2_daily"],
                "m_util": plant.m_util,
                "w_util": plant.w_util,
                "t2_m" : m,
                "t2_w" : w
            })

    # print(sweep_results)

    return sweep_results, ai_m, ai_w, ga_instance


