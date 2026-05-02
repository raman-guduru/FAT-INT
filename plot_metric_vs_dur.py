import pandas as pd
import matplotlib.pyplot as plt
import os
import argparse

def plot_metrics_vs_rate_and_duration(csv_file, target_error):
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found. Please ensure your sweep script generated the data.")
        return

    # Load the consolidated CSV data
    df = pd.read_csv(csv_file)
    
    # Filter the data for a specific Error Threshold so the graph remains readable
    df_filtered = df[df['Error_Threshold_pct'] == target_error]
    
    if df_filtered.empty:
        print(f"Error: No data found for Error Threshold = {target_error}%.")
        return

    # Get the unique durations tested to create separate lines
    durations = sorted(df_filtered['Duration_sec'].unique())
    
    # Create a 2x2 grid of subplots
    fig, axs = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(f'FAT-INT Telemetry Scaling vs. Flow Rate\n(Fixed at {target_error}% Error Threshold)', 
                 fontsize=16, fontweight='bold')
    
    for d in durations:
        # Filter and sort data for this specific duration
        df_plot = df_filtered[df_filtered['Duration_sec'] == d].sort_values(by='Rate_flows_sec')
        x = df_plot['Rate_flows_sec']
        
        # Subplot 1: Sampling Ratio
        axs[0, 0].plot(x, df_plot['Sampling_Ratio_pct'], marker='o', linewidth=2, label=f'Duration = {d}s')
        axs[0, 0].set_title('Sampling Ratio vs Flow Rate', fontsize=12)
        axs[0, 0].set_ylabel('Required Sampling Ratio (%)', fontsize=11)
        axs[0, 0].grid(True, linestyle='--', alpha=0.7)

        # Subplot 2: Queue Space (S_Queue)
        axs[0, 1].plot(x, df_plot['S_Queue'], marker='s', linewidth=2, label=f'Duration = {d}s')
        axs[0, 1].set_title('Queue Space ($S_{queue}$) vs Flow Rate', fontsize=12)
        axs[0, 1].set_ylabel('Allocated Bits', fontsize=11)
        axs[0, 1].grid(True, linestyle='--', alpha=0.7)

        # Subplot 3: Hop Space (S_Hop)
        axs[1, 0].plot(x, df_plot['S_Hop'], marker='^', linewidth=2, label=f'Duration = {d}s')
        axs[1, 0].set_title('Hop Space ($S_{hop}$) vs Flow Rate', fontsize=12)
        axs[1, 0].set_xlabel('Flow Rate (flows/sec)', fontsize=11)
        axs[1, 0].set_ylabel('Allocated Bits', fontsize=11)
        axs[1, 0].grid(True, linestyle='--', alpha=0.7)

        # Subplot 4: Egress Space (S_Egress)
        axs[1, 1].plot(x, df_plot['S_Egress'], marker='d', linewidth=2, label=f'Duration = {d}s')
        axs[1, 1].set_title('Egress Space ($S_{egress}$) vs Flow Rate', fontsize=12)
        axs[1, 1].set_xlabel('Flow Rate (flows/sec)', fontsize=11)
        axs[1, 1].set_ylabel('Allocated Bits', fontsize=11)
        axs[1, 1].grid(True, linestyle='--', alpha=0.7)

    # Extract handles and labels for a single unified legend
    handles, labels = axs[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper right', bbox_to_anchor=(0.98, 0.96), title='Analysis Duration', fontsize=10)
    
    # Adjust layout to prevent text clipping
    plt.tight_layout(rect=[0, 0.03, 1, 0.92])
    
    # Save the high-resolution image
    filename = f"sweep_results/FAT_INT_Rate_vs_Duration_{target_error}pct.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Saved graph: {filename}")
    
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot FAT-INT metrics across Flow Rate and Duration")
    parser.add_argument('-e', '--error', type=float, default=2.0, help='The fixed Error Threshold (%) to plot (default: 2.0)')
    parser.add_argument('-f', '--file', type=str, default='sweep_results/consolidated_results.csv', help='Path to consolidated CSV data')
    args = parser.parse_args()
    
    plot_metrics_vs_rate_and_duration(args.file, args.error)