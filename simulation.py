import simpy
import random
import numpy as np
from config import CONFIG

class Plant:
    def __init__(self, env, n_machines, n_workers, **kwargs):
        self.env = env
        self.machine = simpy.Resource(env, capacity=n_machines)
        self.worker = simpy.Resource(env, capacity=n_workers)
        
        # Unpack from kwargs
        self.p_min = kwargs.get("p_min")
        self.p_max = kwargs.get("p_max")
        
        # --- INITIALIZE QUEUE TRACKERS HERE ---
        self.m_queue_history = []
        self.w_queue_history = []
        self.total_queue_history = []

        # --- OTHER TRACKERS ---
        self.all_records = []
        self.parts_done = 0
        self.all_lead_times = []
        self.total_machine_busy_time = 0
        self.total_worker_busy_time = 0
        self.m_util = 0
        self.w_util = 0

    def monitor_queue(self):
        """Record backlog every 1 minute."""
        while True:
            m_queue = len(self.machine.queue)
            w_queue = len(self.worker.queue)
            
            # Store as a tuple or separate lists
            self.m_queue_history.append(m_queue)
            self.w_queue_history.append(w_queue)
            self.total_queue_history.append(m_queue + w_queue)
            
            yield self.env.timeout(1)

    def process_part(self):
        # 1. Capture Entry Time (Start of Queue)
        start_time = self.env.now # Mark when part arrives

        # Request both a machine AND a worker to start
        with self.machine.request() as m_req, self.worker.request() as w_req:
            # The simulation pauses here until BOTH are free
            yield m_req & w_req

            # 2. Capture Grant Time (End of Queue / Start of Process)
            grant_time = self.env.now

            # 3. Calculate and execute processing
            # print(f"DEBUG: p_min = {self.p_min}, p_max = {self.p_max}")
            duration = random.uniform(self.p_min, self.p_max)
            # print(f"DEBUG: duration = {duration}")
            yield self.env.timeout(duration)

            # 4. Capture Completion Time
            end_time = self.env.now

            # --- CALCULATIONS ---
            wait_time = grant_time - start_time
            work_time = end_time - grant_time  # This will match 'duration'
            lead_time = end_time - start_time

            # --- STORAGE ---
            # Storing as a dictionary makes it much easier to plot later
            self.all_records.append({
                "wait_time": wait_time,
                "work_time": work_time,
                "lead_time": lead_time,
                "exit_time": end_time
            })
            self.all_lead_times.append(lead_time)
            self.parts_done += 1
            # Track busy time for both
            self.total_machine_busy_time += work_time
            self.total_worker_busy_time += work_time


def run_simulation(config):
    # print("DEBUG: run_simulation started")

    # -- part generator function --
    def part_generator(env):
        arrival_rate = config["arrival_rate"]
        while True:
            env.process(plant.process_part())

            # Round to 2 decimal places (e.g., 7.58)
            # This removes the "infinite precision" noise
            clean_interval = round(float(arrival_rate), 2)
            # print(f"DEBUG: arrival_rate = {clean_interval}")

            yield env.timeout(clean_interval)

    # 1. Get the seed from the config, or use a default 
    # -- allows the random number generator to produce the exact same sequence of "random" process times every run --
    seed_val = config.get("seed", None)
    random.seed(seed_val)
    np.random.seed(seed_val)

    # 2. Determine which M and W to use
    # --- MODE: CAPACITY STRESS TEST (TAB 1) ---
    if config.get("mode") == "stress_test":
        # Tab 1: Use the 'Fixed' values from the UI
        m = config["t1_m"]
        w = config["t1_w"]

    # --- MODE: RESOURCE OPTIMIZER (TAB 2) ---
    elif config.get("mode") == "optimizer":
        # Tab 2: Use the 'AI-Generated' values from the GA DNA
        # (We will inject these into the config inside engine.py)
        m = config.get("t2_m", random.uniform(CONFIG["range_machines"][0], CONFIG["range_machines"][1]))
        w = config.get("t2_w", random.uniform(CONFIG["range_workers"][0], CONFIG["range_workers"][1]))

    # print(f"DEBUG: n_machines = {m}")
    # print(f"DEBUG: n_workers = {w}")

    # 3. Initialise simulation and plant variables
    env = simpy.Environment()
    plant = Plant(env, n_machines=m, n_workers=w, **config)  

    # 4. Execute simulation
    total_simulation_time = config["shift_length"] * 60

    env.process(plant.monitor_queue())
    env.process(part_generator(env))
    env.run(until=total_simulation_time)

    # --- 5. Calculate final utilisation percentages ---
    # Machine Util = (Busy Time) / (Total Time * Number of Machines)
    plant.m_util = (plant.total_machine_busy_time / (total_simulation_time * m)) * 100
    
    # Worker Util = (Busy Time) / (Total Time * Number of Workers)
    plant.w_util = (plant.total_worker_busy_time / (total_simulation_time * w)) * 100
    
    return plant