import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- TAB 1: Maximum Demand ---
def display_stress_test_results(session_state):    
    # --- AI Results ---
    df_results = pd.DataFrame(session_state.t1_sweep_results)
    ai_limit_found = session_state.t1_limit_found
    target_lead_time = session_state.t1_lead_time_limit

    limit_row = df_results[df_results["arrival_rate"] == ai_limit_found]
    if not limit_row.empty:
        m_util = limit_row["m_util"].iloc[0] 
        w_util = limit_row["w_util"].iloc[0]
        est_lead_time = limit_row["est_lead_time"].iloc[0]
        parts_done = limit_row["parts_done"].iloc[0]

    else:
        m_util = 0.0
        w_util = 0.0
        est_lead_time = 0.0
        parts_done = 0.0
    
    # Calculate production rate (PPM)   
    ppm = 1 / ai_limit_found if ai_limit_found > 0 else 0

    # Identify the primary bottleneck at the first failure point
    failure_row = df_results[df_results['within_sla'] == False].iloc[0] if not df_results['within_sla'].all() else None

    if failure_row is not None:
        m_q = failure_row['max_machine_queue']
        w_q = failure_row['max_worker_queue']
        
        bottleneck = "Machines" if m_q >= w_q else "Workers"
        severity = m_q if m_q > w_q else w_q

    # --- AI Advice ---
    st.write("---")
    st.subheader("🤖 AI Optimization Advice")

    # Simple heuristic: Adding a resource usually improves capacity by ~30-40% 
    # in a balanced system (this is a common industrial estimate)
    estimated_improvement = ai_limit_found * 0.7

    st.success(f"""
        ##### ✅ The AI Engine has determined that your factory's **sustainable limit** is:
        * **Arrival Rate:** {ai_limit_found:.2f} min/part ({ppm:.2f} part/min)
        * **Daily Output:** {parts_done} units per day (Shift = {session_state.global_shift} hrs)
        * **Average Lead Time:** {est_lead_time} minutes

        *Operating at a faster rate than {ai_limit_found:.2f} min/part is likely to cause a bottleneck, increasing queue and lead time exponentially.*
    """)

    if "Workers" in bottleneck:
        st.info(
            f"💡 **Recommendation:** Your workers are the primary constraint at the **{ai_limit_found:.2f} min/part** threshold. "
            f"Since machines still have idle capacity, consider adding **one additional worker** to increase your throughput capacity. "
        )
    else:
        st.info(
            f"💡 **Recommendation:** Your machines reached maximum utilization at **{ai_limit_found:.2f} min/part**. "
            f"Your current staff of **{session_state.t1_w} workers** is sufficient, but the hardware is the bottleneck. "
            "Consider adding a **secondary station** or a high-speed machine to increase your throughput capacity."
        )    

    # --- AI ENGINE RESULTS ---
    st.write("---")
    st.subheader("🤖 AI Engine Insights")

    with st.expander("More Details on AI Results", expanded=True):
        if session_state.get("t1_ga_status"):
            status = session_state['t1_ga_status']
            
            if status["type"] == "success":
                st.success(status["msg"])
            else:
                st.warning(status["msg"])
    
        # Visualizing the "Learning" process
        tab1, tab2 = st.tabs(["🧬 AI Exploration Range", "📈 Fitness Curve"])
        
        with tab1:
            # --- CHART 1 ---
            st.write("AI exploration range:")
            plt.clf()
            fig_gene = session_state.t1_ga_instance.plot_genes(graph_type="boxplot")
            fig_gene.set_size_inches(10, 5)
            plt.xticks([])
            plt.xlabel("Arrival Rate (min/part)")
            st.pyplot(fig_gene)
            plt.close(fig_gene)

            # --- CHART 2 ---            
            st.write("AI exploration range over time:")
            # -- Data Extraction --
            all_sols = session_state.t1_ga_instance.solutions
            pop_size = session_state.t1_ga_instance.sol_per_pop
            num_gens = session_state.t1_ga_instance.generations_completed

            gen_mins, gen_maxs, gen_means = [], [], []
            
            for g in range(num_gens + 1):
                # Get all solutions for this specific generation
                start_idx = g * pop_size
                end_idx = (g + 1) * pop_size
                current_gen_genes = [s[0] for s in all_sols[start_idx:end_idx]]
                
                gen_mins.append(min(current_gen_genes))
                gen_maxs.append(max(current_gen_genes))
                gen_means.append(sum(current_gen_genes) / len(current_gen_genes))

            # -- Plot Graph --
            fig_gene_all, ax = plt.subplots(figsize=(10, 5))
            x_range = range(len(gen_mins))
            
            # Shaded Area (The "Exploration Zone")
            ax.fill_between(x_range, gen_mins, gen_maxs, color='#636efa', alpha=0.2, label="Search Range")
            
            # Mean Line
            ax.plot(x_range, gen_means, color='#636efa', linewidth=2, label="Average Arrival Rate Tested")
            
            # 3. Apply Styling (Using your refactored logic)
            ax.set_title("Arrival Rate: Min/Max per Generation", pad=15)
            ax.set_xlabel("Generation")
            ax.set_ylabel("Arrival Rate (min/part)")
            
            # Style to match your Dark Theme
            ax.grid(True, alpha=0.1)
            ax.legend(facecolor='#1e1e1e', edgecolor='#444444', labelcolor='white')
            
            st.pyplot(fig_gene_all)
            plt.close(fig_gene_all)

        with tab2:
            # --- CHART 1 ---
            st.write("Evolution of solution quality over time:")
            plt.clf()
            fig_fitnesss = session_state.t1_ga_instance.plot_fitness(color="#00cc96")
            fig_fitnesss.set_size_inches(10, 5)
            plt.ylabel("Fitness (Higher = Better)")
            st.pyplot(fig_fitnesss)
            plt.close(fig_fitnesss)
            
            # --- CHART 2 ---
            st.write("Evolution of AI recommendation over time:")
            plt.clf()
            best_solutions = session_state.t1_ga_instance.best_solutions
                
            # Extract the first gene (Arrival Interval) from each best solution
            best_intervals = [sol[0] for sol in best_solutions]
            
            # 2. Create a clean, standardized plot
            fig, ax = plt.subplots(figsize=(10, 5))
            
            # Plot the 'Path' the AI took to find the limit
            ax.step(range(len(best_intervals)), best_intervals, where='post', 
                    color='#636efa', linewidth=2, label="Best Interval")
            
            # Formatting
            ax.set_title("Best Arrival Rate per Generation")
            ax.set_xlabel("Generation")
            ax.set_ylabel("Arrival Rate (min/part)")
            
            ax.grid(True, alpha=0.2)
            
            st.pyplot(fig)
            plt.close(fig)

    # --- SUMMARY RESULTS ---
    st.write("---")
    st.subheader("📊 Factory Stress Profile")
        
    st.error(f"⚠️ **Primary Bottleneck Detected:** {bottleneck}")
    st.caption(f"System failure begins at Arrival Interval {failure_row['arrival_rate']} due to {bottleneck} backlog ({severity} items).")

    # --- ROW 1: SIMULATION RESULTS ---
    with st.container(border=False):
        st.markdown("#### Results from Simulation")
        m1, m2 = st.columns(2)

        with m1:
            st.caption("##### AI Discovered Optimisation")

            sub_m1_col1, sub_m1_col2 = st.columns(2)

            # Column 1: The AI's Result
            with sub_m1_col1:
                st.write("Arrival Rate")
                # Use h3 or h4 for a smaller, non-truncated number
                st.markdown(f"#### {ai_limit_found:.2f} min/part")
                st.markdown(f":blue-background[**{ppm:.2f} parts/min**]")

            # Column 2: The Goal (SLA)
            with sub_m1_col2:
                st.write("Average Lead Time")
                st.markdown(f"#### {est_lead_time:.2f} mins")
                
                buffer = session_state.t1_lead_time_limit - est_lead_time
                m2_color = "red" if buffer < 0 else "green"
                st.markdown(f":{m2_color}-background[**{buffer:.2f} mins buffer**]")

        # Column 3: Resource Utilization (Efficiency)
        with m2:
            # Assuming 'failure_row' or 'limit_data' contains your % values
            # We show them stacked inside the third column for a clean look
            st.caption("##### Resource Utilization")
            
            # Create a sub-grid inside Column 3
            sub_m2_col1, sub_m2_col2 = st.columns(2)
            
            # --- Machine Utilization (Sub-Column 1) ---
            with sub_m2_col1:
                m_idle = 100 - m_util
                st.write("Machine")
                st.markdown(f"#### {m_util:.2f}%")
                st.markdown(f":green-background[**{m_idle:.1f}% Idle**]")
            
            # --- Worker Utilization (Sub-Column 2) ---
            with sub_m2_col2:
                w_idle = 100 - w_util
                st.write("Worker")
                st.markdown(f"#### {w_util:.2f}%")
                st.markdown(f":green-background[**{w_idle:.1f}% Idle**]")

    # --- ROW 2: FINANCIALS ---
    st.divider()  # Creates a clean horizontal line
    st.markdown(f"#### Financials per Day (Shift = {session_state.global_shift} hrs)")
    with st.container(border=False):
        f1, f2 = st.columns(2)

        with f1:
            st.caption("##### Profitability")
            sub_f1_col1, sub_f1_col2 = st.columns(2)

            # Column 1: Revenue Volume
            with sub_f1_col1:
                st.write("Revenue")
                earnings = parts_done * session_state.global_rev

                st.markdown(f"#### ${earnings:,.2f}")
                st.markdown(f":blue-background[**{int(parts_done)} Units Produced**]")

            # Column 2: The "Bottom Line"
            with sub_f1_col2:
                st.write("Net Profit")

                m_cost_total = session_state.t1_m * session_state.global_m_cost
                w_cost_total = session_state.t1_w * (session_state.global_shift * session_state.global_w_cost)
                total_cost = m_cost_total + w_cost_total
                profit = earnings - total_cost
                margin = (profit / earnings * 100) if earnings > 0 else 0
                f2_color = "red" if profit < 0 else "green"
                
                st.markdown(f"#### ${profit:,.2f}")
                st.markdown(f":{f2_color}-background[**{margin:.1f}% Margin**]")

        # Column 3: Cost Breakdown (Side-by-Side)
        with f2:
            st.caption("##### Operating Costs")

            sub_f3_col1, sub_f3_col2 = st.columns(2)
            with sub_f3_col1:
                st.write("Machine")
                st.markdown(f"#### ${m_cost_total:,.0f}")
                st.markdown(f":blue-background[**{session_state.t1_m} Units**]")

            with sub_f3_col2:
                st.write("Worker")
                st.markdown(f"#### ${w_cost_total:,.0f}")
                st.markdown(f":blue-background[**{session_state.t1_w} Workers**]")

    # --- ROW 3: CHART ---
    # 1. Create subplots with a secondary axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 2. Add Total Output (Area)
    fig.add_trace(
        go.Scatter(
            x=df_results['arrival_rate'],
            y=df_results['parts_done'],
            name="Total Output (units)",
            fill='tozeroy',
            # Use a neutral gray that works in both light and dark
            fillcolor='rgba(128, 128, 128, 0.15)',
            line=dict(color='rgba(128, 128, 128, 0)', width=0), 
            mode='lines',
            hovertemplate='Daily Output: %{y:.0f} units<extra></extra>'
        ),
        secondary_y=True,
    )

    # 3. Add Lead Time (Line) + Custom Tooltip
    fig.add_trace(
        go.Scatter(
            x=df_results['arrival_rate'], 
            y=df_results['est_lead_time'],
            name="Lead Time",
            mode='lines+markers',
            line=dict(color='#29b5e8', width=2, shape='spline'),
            # This is your "Tool Tip" configuration
            customdata=df_results[['w_util', 'm_util']], # Pass extra data here
            hovertemplate=(
                "Arrival Rate: %{x} min/part<br>" +
                "Lead Time: %{y:.1f} mins<br>" +
                "Worker Utilization: %{customdata[0]:.1f}%<br>" +
                "Machine Utilization: %{customdata[1]:.1f}%<extra></extra>"
            ),
        ),
        secondary_y=False
    )

    # 4. Add the SLA Line (Left Axis)
    sla_val = session_state.get('t1_lead_time_limit')
    fig.add_hline(
        y=sla_val, 
        line_dash="dash", 
        line_color="#ff4b4b",
        line_width=1, # Thinner line 
        annotation_text="Max Acceptable Lead Time", 
        annotation_position="top left",
        annotation_font=dict(size=10, color="rgba(255, 75, 75, 0.8)")
    )
    
    # 5. Add Vertical AI Recommended Limit
    fig.add_vline(
        x=ai_limit_found, 
        line_dash="dot", 
        line_color="#01a26f", # Emerald Green for "Recommended"
        line_width=2,
        annotation_text="AI Recommended Limit", 
        annotation_position="top right",
        annotation_font=dict(size=10, color="#00cc96")
    )

    # 6. Styling
    fig.update_layout(\
        showlegend=False,
        template="none", # Uses Streamlit's system theme
        hovermode="x unified", # Shows all data for that X-value in one box
        # This forces the tooltip box to be solid and readable
        hoverlabel=dict(
            bgcolor="white"
        ),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title="Arrival Interval (min/part) - Stress Increases Right →",
            color="#6c757d", 
            autorange="reversed",
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.1)', # Very faint gray
            gridwidth=0.5,                        # Thinner lines
            tickfont=dict(size=10, color='gray'), # Smaller numbers
        ),
        yaxis=dict(
            title="Lead Time (mins)", 
            color="#29b5e8", 
            gridcolor='rgba(128, 128, 128, 0.1)', # Faint horizontal lines
            gridwidth=0.5,
            tickfont=dict(size=10),
            ticksuffix="  ",
        ),
        yaxis2=dict(
            title="Total Output (units)", 
            color="#6c757d", 
            showgrid=False, # Keeps the right side clean
            tickfont=dict(size=10),
            ticksuffix="  ",
        ),
    )

    st.divider()  # Creates a clean horizontal line
    st.write("#### Capacity Stress Test")
    st.plotly_chart(fig, width="stretch", theme="streamlit")

    # --- ROW 4: TABLE ---
    # 1. Define the columns you actually want to display
    display_cols = [
        "arrival_rate", 
        "parts_done",
        "est_lead_time",  
        "w_util", 
        "m_util", 
        "max_machine_queue",
        "max_worker_queue",
        "within_sla"
    ]

    df_display = df_results[display_cols]

    # 2. Define a styling function to highlight the 'Failure Zone'
    def style_failure(row):
        # If 'within_sla' is False, highlight the whole row in light red
        color = 'background-color: rgba(255, 75, 75, 0.15)' if not row.within_sla else ''
        return [color] * len(row)

    styled_df = df_results.style.apply(style_failure, axis=1).format({
        "arrival_rate":"{:.2f}",
        "parts_done":"{:,.0f}",
        "est_lead_time":"{:.2f}",
        "w_util":"{:.1f}",
        "m_util":"{:.1f}", 
        "max_machine_queue":"{:,.0f}",
        "max_worker_queue":"{:,.0f}"
    })

    # 3. Display with custom column formatting
    st.write("### 📊 Simulation Batch Analysis")
    st.caption("Detailed breakdown of factory performance across different arrival intervals.")

    # You can use 'column_order' to further refine the look
    st.dataframe(
        styled_df, 
        width="stretch", 
        hide_index=True,
        column_order=(
            "arrival_rate", 
            "parts_done",
            "est_lead_time",
            "within_sla",  
            "w_util", 
            "m_util", 
            "max_machine_queue",
            "max_worker_queue",
        ),
        column_config={
            "arrival_rate": "Arrival Interval (min/part)",
            "parts_done": "Total Output (units)",
            "est_lead_time": "Average Lead Time (min)",
            "w_util": "Worker Utilization (%)",
            "m_util": "Machine Utilization (%)",
            "max_machine_queue": "Max Machine Queue (units)", # Added rename
            "max_worker_queue": "Max Worker Queue (units)",   # Added rename
            "within_sla": "Within Limits"
        }
    )

# --- TAB 2: Optimizer ---
def display_optimizer_results(session_state):    
    # --- AI Results ---
    st.write("---")
    st.subheader("🤖 AI Investment Recommendation")

    # Get best solution from state
    rec_m = st.session_state.t2_m
    rec_w = st.session_state.t2_w

    df_results = pd.DataFrame(session_state.t2_sweep_results)

    limit_row = df_results[(df_results["t2_m"] == rec_m) & (df_results["t2_w"] == rec_w)
                           ]
    if not limit_row.empty:
        m_util = limit_row["m_util"].iloc[0] 
        w_util = limit_row["w_util"].iloc[0]
        est_lead_time = limit_row["est_lead_time"].iloc[0]
        parts_done = limit_row["parts_done"].iloc[0]
        target_demand = limit_row["daily_target"].iloc[0]
        arrival_rate = limit_row["arrival_rate"].iloc[0]
    else:
        m_util = 0.0
        w_util = 0.0
        est_lead_time = 0.0
        parts_done = 0.0
        target_demand = st.session_state.t2_daily
        arrival_rate = st.session_state.t2_arr


    # Logic: Is the configuration "Tight" or "Comfortable"?
    # We compare the target daily output to what was actually achieved in the best sim

    st.success(f"""
        ##### ✅ The AI Engine recommends the following **Optimal Configuration**:
        * **Machine Count:** {rec_m} Units
        * **Worker Count:** {rec_w} Workers

        **Performance at this level with parts arrival interval of {arrival_rate} min/part:**
        * **Daily Output:** {parts_done} / {target_demand} units
        * **Machine Utilization:** {m_util:.1f}%
        * **Worker Utilization:** {w_util:.1f}%
    """)

    # --- Cost & Efficiency Insight ---
    # Logic: If machines == workers, it's a 1:1 setup. If not, explain why.
    if rec_m > rec_w:
        st.info(
            f"💡 **Efficiency Insight:** The AI found that you can save costs by having **{rec_m} machines** shared by only **{rec_w} workers**. "
            "This indicates your process is 'worker-constrained'—adding more staff would be more expensive than letting machines sit idle occasionally."
        )
    elif rec_w > rec_m:
        st.info(
            f"💡 **Efficiency Insight:** The AI recommends a surplus of staff (**{rec_w} workers** for **{rec_m} machines**). "
            "This suggests your machine cycle times are the primary bottleneck. Extra staff are being used to ensure machines never stop running."
        )
    else:
        st.info(
            "💡 **Efficiency Insight:** A **1:1 balanced ratio** was found to be the most cost-effective. "
            "This setup minimizes idle time for both your human and hardware capital while precisely meeting your daily target."
        )

    # --- AI ENGINE RESULTS ---
    st.write("---")
    st.subheader("🤖 AI Engine Insights")

    with st.expander("More Details on AI Results", expanded=True):
        if session_state.get("t2_ga_status"):
            status = session_state['t2_ga_status']
            
            if status["type"] == "success":
                st.success(status["msg"])
            else:
                st.warning(status["msg"])
    
        # Visualizing the "Learning" process
        tab1, tab2 = st.tabs(["🧬 AI Exploration Range", "📈 Fitness Curve"])
        
        with tab1:
            # --- CHART 1 ---
            st.write("AI exploration range:")
            plt.clf()
            fig_gene = session_state.t2_ga_instance.plot_genes(graph_type="boxplot")
            fig_gene.set_size_inches(10, 5)
            plt.xticks([1, 2], ["Machines", "Workers"], fontsize=10)
            plt.xlabel("Resource Type")
            plt.ylabel("Number of Units")
            st.pyplot(fig_gene)
            plt.close(fig_gene)

            # --- CHART 2 ---            
            st.write("AI exploration range over time:")
            # -- Data Extraction --
            all_sols = session_state.t2_ga_instance.solutions
            pop_size = session_state.t2_ga_instance.sol_per_pop
            num_gens = session_state.t2_ga_instance.generations_completed

            # gen_mins, gen_maxs, gen_means = [], [], []

            # Data structures for both genes
            m_stats = {"min": [], "max": [], "mean": []}
            w_stats = {"min": [], "max": [], "mean": []}
            
            for g in range(num_gens + 1):
                # Get all solutions for this specific generation
                start_idx = g * pop_size
                end_idx = (g + 1) * pop_size
                current_gen_genes = all_sols[start_idx:end_idx]
                
                # gen_mins.append(min(current_gen_genes))
                # gen_maxs.append(max(current_gen_genes))
                # gen_means.append(sum(current_gen_genes) / len(current_gen_genes))

                # Extract Gene 0 (Machines) and Gene 1 (Workers)
                m_vals = [s[0] for s in current_gen_genes]
                w_vals = [s[1] for s in current_gen_genes]

                # Store Machine Stats
                m_stats["min"].append(min(m_vals))
                m_stats["max"].append(max(m_vals))
                m_stats["mean"].append(sum(m_vals) / len(m_vals))
                
                # Store Worker Stats
                w_stats["min"].append(min(w_vals))
                w_stats["max"].append(max(w_vals))
                w_stats["mean"].append(sum(w_vals) / len(w_vals))
                
            # -- Plot Graph --
            fig_gene_all, ax = plt.subplots(figsize=(10, 5))
            x_range = range(len(m_stats["mean"]))
            
            # Shaded Area (The "Exploration Zone")
            ax.fill_between(x_range, m_stats["min"], m_stats["max"], color='#636efa', alpha=0.15, label="Machine Search Range")
            ax.fill_between(x_range, w_stats["min"], w_stats["max"], color='#ef553b', alpha=0.15, label="Worker Search Range")

            # Mean Line
            ax.plot(x_range, m_stats["mean"], color='#636efa', linewidth=2.5, label="Avg Machines Tested", marker='o', markersize=4)
            ax.plot(x_range, w_stats["mean"], color='#ef553b', linewidth=2.5, label="Avg Workers Tested", marker='s', markersize=4)                
            
            # 3. Apply Styling (Using your refactored logic)
            ax.set_title("Machines and Workers: Min/Max per Generation", pad=15)
            ax.set_xlabel("Generation")
            ax.set_ylabel("Number of Units")     

            # Style to match your Dark Theme
            ax.grid(True, alpha=0.1)
            ax.legend(facecolor='#1e1e1e', edgecolor='#444444', labelcolor='white')
            
            st.pyplot(fig_gene_all)
            plt.close(fig_gene_all)

        with tab2:
            # --- CHART 1 ---
            st.write("Evolution of solution quality over time:")
            plt.clf()
            fig_fitnesss = session_state.t2_ga_instance.plot_fitness(color="#00cc96")
            fig_fitnesss.set_size_inches(10, 5)
            plt.ylabel("Fitness (Higher = Better)")
            st.pyplot(fig_fitnesss)
            plt.close(fig_fitnesss)
            
            # --- CHART 2 ---
            st.write("Evolution of AI recommendation over time:")
            plt.clf()
            best_solutions = session_state.t2_ga_instance.best_solutions
                
            # Extract Gene 0 (Machines) and Gene 1 (Workers)
            best_m_path = [sol[0] for sol in best_solutions]
            best_w_path = [sol[1] for sol in best_solutions]      

            # 2. Create a clean, standardized plot
            fig, ax = plt.subplots(figsize=(10, 5))
            gen_range = range(len(best_m_path))
            
            # Plot the 'Step' path for both resources
            ax.step(gen_range, best_m_path, where='post', color='#636efa', linewidth=2.5, label="Best Machine Count")
            ax.step(gen_range, best_w_path, where='post', color='#ef553b', linewidth=2.5, label="Best Worker Count")

            # Formatting
            ax.set_title("Best Machine and Worker Counts per Generation")
            ax.set_xlabel("Generation")
            ax.set_ylabel("Number of Units")
            ax.legend(facecolor='#1e1e1e', edgecolor='#444444', labelcolor='white')
            
            ax.grid(True, alpha=0.2)
            
            st.pyplot(fig)
            plt.close(fig)

    # --- SUMMARY RESULTS ---
    st.write("---")
    st.subheader("📊 Factory Stress Profile")
        
    # --- ROW 1: SIMULATION RESULTS ---
    with st.container(border=False):
        st.markdown("#### Results from Simulation")
        m1, m2 = st.columns(2)

        with m1:
            st.caption("##### AI Discovered Optimisation")

            sub_m1_col1, sub_m1_col2 = st.columns(2)

            # Column 1: The AI's Result
            with sub_m1_col1:
                st.write("Machine Count")
                # Use h3 or h4 for a smaller, non-truncated number
                st.markdown(f"#### {rec_m} Units")

            with sub_m1_col2:
                st.write("Worker Count")
                st.markdown(f"#### {rec_w} Workers")
                
        # Column 3: Resource Utilization (Efficiency)
        with m2:
            # Assuming 'failure_row' or 'limit_data' contains your % values
            # We show them stacked inside the third column for a clean look
            st.caption("##### Resource Utilization")
            
            # Create a sub-grid inside Column 3
            sub_m2_col1, sub_m2_col2 = st.columns(2)
            
            # --- Machine Utilization (Sub-Column 1) ---
            with sub_m2_col1:
                m_idle = 100 - m_util
                st.write("Machine")
                st.markdown(f"#### {m_util:.2f}%")
                st.markdown(f":green-background[**{m_idle:.1f}% Idle**]")
            
            # --- Worker Utilization (Sub-Column 2) ---
            with sub_m2_col2:
                w_idle = 100 - w_util
                st.write("Worker")
                st.markdown(f"#### {w_util:.2f}%")
                st.markdown(f":green-background[**{w_idle:.1f}% Idle**]")

    # --- ROW 2: FINANCIALS ---
    st.divider()  # Creates a clean horizontal line
    st.markdown(f"#### Financials per Day (Shift = {session_state.global_shift} hrs)")
    with st.container(border=False):
        f1, f2 = st.columns(2)

        with f1:
            st.caption("##### Profitability")
            sub_f1_col1, sub_f1_col2 = st.columns(2)

            # Column 1: Revenue Volume
            with sub_f1_col1:
                st.write("Revenue")
                earnings = parts_done * session_state.global_rev

                st.markdown(f"#### ${earnings:,.2f}")
                st.markdown(f":blue-background[**{int(parts_done)} Units Produced**]")

            # Column 2: The "Bottom Line"
            with sub_f1_col2:
                st.write("Net Profit")

                m_cost_total = session_state.t2_m * session_state.global_m_cost
                w_cost_total = session_state.t2_w * (session_state.global_shift * session_state.global_w_cost)
                total_cost = m_cost_total + w_cost_total
                profit = earnings - total_cost
                margin = (profit / earnings * 100) if earnings > 0 else 0
                f2_color = "red" if profit < 0 else "green"
                
                st.markdown(f"#### ${profit:,.2f}")
                st.markdown(f":{f2_color}-background[**{margin:.1f}% Margin**]")

        # Column 3: Cost Breakdown (Side-by-Side)
        with f2:
            st.caption("##### Operating Costs")

            sub_f3_col1, sub_f3_col2 = st.columns(2)
            with sub_f3_col1:
                st.write("Machine")
                st.markdown(f"#### ${m_cost_total:,.0f}")
                st.markdown(f":blue-background[**{session_state.t2_m} Units**]")

            with sub_f3_col2:
                st.write("Worker")
                st.markdown(f"#### ${w_cost_total:,.0f}")
                st.markdown(f":blue-background[**{session_state.t2_w} Workers**]")

    # --- ROW 3: CHART ---
    st.divider()  # Creates a clean horizontal line
    st.write("#### Capacity Stress Test")

    # 1. Calculate Metrics
    df_results['total_cost'] = (df_results['t2_m'] * session_state.global_m_cost) + (df_results['t2_w'] * (session_state.global_shift * session_state.global_w_cost))
    df_results['total_revenue'] = df_results['parts_done'] * session_state.global_rev
    df_results['net_profit'] = df_results['total_revenue'] - df_results['total_cost']

    # 2. Create the Plot
    # 1. Initialize Figure
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.style.use('ggplot')

    # 1. Main Scatter Plot
    colors = ['#27ae60' if met else '#e74c3c' for met in df_results['target_met']]

    scatter = ax.scatter(
        df_results['total_cost'],
        df_results['total_revenue'],
        c=colors,                # Use the conditional color list
        s=140, 
        edgecolors='white', 
        linewidth=0.8,
        zorder=3,
        alpha=0.85               # Slight transparency for overlapping points
    )

    # 2. Advanced Smart Labels
    # We filter for the best unique machine count to prevent clustering
    df_labels = df_results.sort_values('net_profit', ascending=False).drop_duplicates('t2_m')

    for i, row in df_labels.iterrows():
        # Create a "Speech Bubble" effect for the label
        ax.annotate(
            f"{int(row.t2_m)}M:{int(row.t2_w)}W",
            (row.total_cost, row.total_revenue),
            xytext=(12, 0),             # Clear horizontal offset
            textcoords='offset points',
            fontsize=9,
            fontweight='bold',
            va='center',
            bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='none', alpha=0.7) # Added background box
        )

    # 3. Breakeven Line & Shading
    limit = max(df_results['total_cost'].max(), df_results['total_revenue'].max()) * 1.1
    ax.plot([0, limit], [0, limit], color='#e74c3c', linestyle='--', alpha=0.6, label="Breakeven", zorder=1)
    
    # Optional: Light shade for the "Profit Zone"
    ax.fill_between([0, limit], [0, limit], limit, color='green', alpha=0.02)

    # 4. Final Polish
    ax.set_title("Economic Trade-offs", fontsize=15, fontweight='bold', pad=20)
    ax.set_xlabel("Daily Total Operating Cost ($)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Daily Total Revenue ($)", fontsize=11, fontweight='bold')
    
    # Force a 1:1 aspect ratio visually
    ax.set_xlim(0, limit)
    ax.set_ylim(0, limit)
    
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label=f'Daily Target ({target_demand} Units) Met',
            markerfacecolor='#27ae60', markersize=10),
        Line2D([0], [0], marker='o', color='w', label=f'Daily Target ({target_demand} Units) Not Met',
            markerfacecolor='#e74c3c', markersize=10),
        Line2D([0], [0], color='#e74c3c', linestyle='--', label='Breakeven')
    ]
    ax.legend(handles=legend_elements, loc='lower right', frameon=True, facecolor='white')

    st.pyplot(fig)
    plt.close(fig)

    # --- ROW 4: TABLE ---
    # 1. Define the columns you actually want to display
    display_cols = [
        "arrival_rate", 
        "t2_m", 
        "t2_w",
        "parts_done",
        "est_lead_time",  
        "w_util", 
        "m_util", 
        "max_machine_queue",
        "max_worker_queue",
        "target_met"
    ]

    df_display = df_results[display_cols]

    # 2. Define a styling function to highlight the 'Failure Zone'
    def style_failure(row):
        # If 'target_met' is False, highlight the whole row in light red
        color = 'background-color: rgba(255, 75, 75, 0.15)' if not row.target_met else ''
        return [color] * len(row)
    
    sorted_df = df_results.sort_values(by="net_profit", ascending=False)

    styled_df = sorted_df.style.apply(style_failure, axis=1).format({
        "arrival_rate":"{:.2f}",
        "parts_done":"{:,.0f}",
        "total_cost":"{:,.0f}",
        "total_revenue":"{:,.0f}",
        "net_profit":"{:,.0f}",
        "est_lead_time":"{:.2f}",
        "w_util":"{:.1f}",
        "m_util":"{:.1f}", 
        "max_machine_queue":"{:,.0f}",
        "max_worker_queue":"{:,.0f}"
    })

    # 3. Display with custom column formatting
    st.divider()  # Creates a clean horizontal line
    st.write("### 📊 Simulation Batch Analysis")
    st.caption("Detailed breakdown of factory performance across Machine-Worker configurations.")

    # You can use 'column_order' to further refine the look
    st.dataframe(
        styled_df, 
        width="stretch", 
        hide_index=True,
        column_order=(
            "t2_m", 
            "t2_w",
            "parts_done",
            "total_cost",
            "total_revenue",
            "net_profit",
            "est_lead_time",
            "target_met",  
            "w_util", 
            "m_util", 
            "max_machine_queue",
            "max_worker_queue",
        ),
        column_config={
            "t2_m": "Machine Count",
            "t2_w": "Worker Count",
            "parts_done": "Total Output (units)",
            "total_cost": "Total Cost ($)",
            "total_revenue": "Total Revenue ($)",
            "net_profit": "Net Profit ($)",
            "est_lead_time": "Average Lead Time (min)",
            "w_util": "Worker Utilization (%)",
            "m_util": "Machine Utilization (%)",
            "max_machine_queue": "Max Machine Queue (units)", # Added rename
            "max_worker_queue": "Max Worker Queue (units)",   # Added rename
            "target_met": "Target Met"
        }
    )

