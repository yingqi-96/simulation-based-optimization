CONFIG = {
    "shift_length": 8,          # 8 hours
    "part_revenue": 150,        # $ per finished part
    "machine_cost": 500,        # Fixed cost per machine
    "worker_wage": 10,      # Daily wage per worker
    "arrival_rate": 5,          # New part every 5 minutes

    "base_process_time": [8, 30],     # The average (Mean)

    # AI Search Space: [Min, Max]
    "range_machines": [1, 20],
    "range_workers": [1, 20],
    "lead_time_limit": 60
}