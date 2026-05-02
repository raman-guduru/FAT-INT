import os
import subprocess
import csv
import sys

def run_command(cmd, cwd=None, capture=False):
    """Executes a terminal command."""
    print(f"\n[EXEC] {cmd}")
    
    if capture:
        # Only capture the output if we explicitly need to parse it (e.g., the profiler)
        result = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)
        if result.returncode != 0:
            print(f"[ERROR] Command failed:\n{result.stderr}")
        return result.stdout
    else:
        # Let the command stream directly to the terminal to prevent sudo/tty issues
        subprocess.run(cmd, shell=True, cwd=cwd)
        return ""

def parse_cutoff_table(output_text, rate, duration, csv_writer):
    """Scrapes the stdout of get_cut-off.py and appends to the master CSV."""
    for line in output_text.split('\n'):
        if '%' in line and '|' in line:
            try:
                parts = [p.strip() for p in line.split('|')]
                err_thresh = float(parts[0].replace('%', ''))
                samp_ratio = float(parts[1])
                s_queue = int(parts[2])
                s_hop = int(parts[3])
                s_egress = int(parts[4])
                
                csv_writer.writerow([duration, rate, err_thresh, samp_ratio, s_queue, s_hop, s_egress])
            except Exception:
                pass 

def main():
    # --- CONFIGURE YOUR SWEEP HERE ---
    rates = [x/100 for x in range(1,100,2)]       # Average flows per second
    durations = [60, 120, 180,240,300,360,420,480]      # Baseline durations in seconds
    # ---------------------------------
    
    os.makedirs("sweep_results", exist_ok=True)
    csv_filename = "sweep_results/consolidated_results.csv"

    print("Starting FAT-INT 2D Parameter Sweep...")
    print(f"Rates: {rates}")
    print(f"Durations: {durations}\n")

    # Get the exact path to the active Python executable (the venv)
    python_cmd = sys.executable

    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Duration_sec', 'Rate_flows_sec', 'Error_Threshold_pct', 'Sampling_Ratio_pct', 'S_Queue', 'S_Hop', 'S_Egress'])
        
        for d in durations:
            for r in rates:
                print(f"\n{'='*60}")
                print(f" RUNNING EXPERIMENT: Duration = {d}s | Rate = {r} flows/s")
                print(f"{'='*60}")
                
                # 1. Generate Flows
                gen_cmd = f"{python_cmd} BMv2/gen_hadoop_flows.py -d BMv2/FbHdp_distribution.txt -t {d} -r {r}"
                run_command(gen_cmd)
                
                # 2. Run Mininet/P4 (Add buffer for switch initialization/teardown)
                make_duration = d + 15
                make_cmd = f"make run FILE_PATH=/home/p4 DURATION={make_duration}"
                # Do NOT capture output here so the Makefile can run cleanly
                run_command(make_cmd, cwd="BMv2", capture=False) 
                
                # 3. Profile and Parse Data
                profile_cmd = f"{python_cmd} BMv2/get_cut-off.py"
                # Capture the output so we can save it to the CSV
                profile_out = run_command(profile_cmd, capture=True)
                
                with open(f"sweep_results/raw_d{d}_r{r}.txt", "w") as raw_f:
                    raw_f.write(profile_out)
                    
                parse_cutoff_table(profile_out, r, d, writer)
                csvfile.flush() 

    print(f"\nAll sweeps complete! Master dataset saved to: {csv_filename}")

if __name__ == "__main__":
    main()



        