import matplotlib.pyplot as plt
import numpy as np
from engine import get_ga_instance, all_scenarios
from config import CONFIG

if __name__ == "__main__":
    print("Initializing AI Optimizer for Plant Simulation...")
    
    ga_instance = get_ga_instance()
    
    print("Running scenarios... please wait.")
    ga_instance.run()
    
    # Get the results
    solution, fitness, idx = ga_instance.best_solution()
    
    print("\n" + "="*30)
    print("OPTIMAL PLANT CONFIGURATION")
    print("="*30)
    print(f"Machines:      {int(solution[0])}")
    print(f"Workers:       {int(solution[1])}")
    print(f"Estimated Daily Profit: ${fitness:,.2f}")
    print("="*30)
    
    # Create a 1x3 dashboard
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 6))

    # --- Figure 1: Manual Fitness Plot (Fixes the 'ax' error) ---
    ax1.plot(ga_instance.best_solutions_fitness, linewidth=3, color="#64f20c")
    ax1.set_title("AI Learning Progress")
    ax1.set_xlabel("Generation")
    ax1.set_ylabel("Fitness (Profit)")
    ax1.grid(True)

    # --- Figure 2: Manual Gene Exploration (Boxplot) ---
    # We grab the solutions history directly
    all_solutions = np.array(ga_instance.solutions)
    # Plotting Machines (Gene 0) and Workers (Gene 1)
    ax2.boxplot([all_solutions[:, 0], all_solutions[:, 1]], labels=["Machines", "Workers"])
    ax2.set_title("Resource Distribution")

    # --- Figure 3: Search Exploration Cloud ---
    data = np.array(all_scenarios) 
    # data[:, 0] = Machines
    # data[:, 1] = Workers
    # data[:, 2] = Profit (Fitness)

    # We use 'c' for color to show Profit, and a fixed 's' (size) for clarity
    scatter = ax3.scatter(
        data[:, 0], 
        data[:, 1], 
        c=data[:, 2],     # Color represents Profit
        cmap='viridis',   # High profit = Yellow, Low profit = Purple
        s=100,            # Fixed size for all dots
        alpha=0.3,        # Transparency shows where dots "stack"
        edgecolors='none'
    )
    
    # Add the colorbar so we know what the colors mean
    cbar = fig.colorbar(scatter, ax=ax3)
    cbar.set_label('Profit ($)', rotation=270, labelpad=15)
    
    ax3.set_title("Search Exploration Cloud")
    ax3.set_xlabel("No. of Machines")
    ax3.set_ylabel("No. of Workers")
    
    # Force the axes to show integer steps (since you can't have 2.5 workers)
    ax3.set_xticks(range(CONFIG["range_machines"][0], CONFIG["range_machines"][1] + 1))
    ax3.set_yticks(range(CONFIG["range_workers"][0], CONFIG["range_workers"][1] + 1))
    ax3.grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.show()