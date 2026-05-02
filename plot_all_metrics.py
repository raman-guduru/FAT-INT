import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_comprehensive_graphs(csv_file):
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found. Run auto_sweep.py first to generate data.")
        return

    # Load the consolidated CSV data
    df = pd.read_csv(csv_file)
    
    # Get the unique durations tested
    durations = df['Duration_sec'].unique()
    
    for d in durations:
        # Filter data for this specific duration
        df_d = df[df['Duration_sec'] == d]
        rates = df_d['Rate_flows_sec'].unique()
        
        # Create a 2x2 grid of subplots for a comprehensive dashboard
        fig, axs = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle(f'FAT-INT Dynamic Telemetry Allocations (Duration = {d}s)', fontsize=18, fontweight='bold')
        
        for r in rates:
            # Filter and sort data for the line plot
            df_plot = df_d[df_d['Rate_flows_sec'] == r].sort_values(by='Error_Threshold_pct')
            x = df_plot['Error_Threshold_pct']
            
            # Subplot 1: Sampling Ratio
            axs[0, 0].plot(x, df_plot['Sampling_Ratio_pct'], marker='o', linewidth=2, label=f'Rate = {r} flows/s')
            axs[0, 0].set_title('Required Sampling Ratio vs Error Threshold', fontsize=12)
            axs[0, 0].set_ylabel('Sampling Ratio (%)', fontsize=11)
            axs[0, 0].grid(True, linestyle='--', alpha=0.7)

            # Subplot 2: Queue Space (S_Queue)
            axs[0, 1].plot(x, df_plot['S_Queue'], marker='s', linewidth=2, label=f'Rate = {r} flows/s')
            axs[0, 1].set_title('Queue Space Allocation ($S_{queue}$) vs Error Threshold', fontsize=12)
            axs[0, 1].set_ylabel('Allocated Bits', fontsize=11)
            axs[0, 1].grid(True, linestyle='--', alpha=0.7)

            # Subplot 3: Hop Space (S_Hop)
            axs[1, 0].plot(x, df_plot['S_Hop'], marker='^', linewidth=2, label=f'Rate = {r} flows/s')
            axs[1, 0].set_title('Hop Space Allocation ($S_{hop}$) vs Error Threshold', fontsize=12)
            axs[1, 0].set_xlabel('Error Threshold (%)', fontsize=11)
            axs[1, 0].set_ylabel('Allocated Bits', fontsize=11)
            axs[1, 0].grid(True, linestyle='--', alpha=0.7)

            # Subplot 4: Egress Space (S_Egress)
            axs[1, 1].plot(x, df_plot['S_Egress'], marker='d', linewidth=2, label=f'Rate = {r} flows/s')
            axs[1, 1].set_title('Egress Space Allocation ($S_{egress}$) vs Error Threshold', fontsize=12)
            axs[1, 1].set_xlabel('Error Threshold (%)', fontsize=11)
            axs[1, 1].set_ylabel('Allocated Bits', fontsize=11)
            axs[1, 1].grid(True, linestyle='--', alpha=0.7)

        # Extract handles and labels for a single unified legend
        handles, labels = axs[0, 0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='upper right', bbox_to_anchor=(0.98, 0.96), title='Network Load', fontsize=10)
        
        # Adjust layout to prevent text clipping
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # Save the high-resolution dashboard image
        filename = f"sweep_results/FAT_INT_Dashboard_{d}s.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Saved comprehensive dashboard: {filename}")
        
        plt.close()

if __name__ == "__main__":
    generate_comprehensive_graphs("sweep_results/consolidated_results.csv")