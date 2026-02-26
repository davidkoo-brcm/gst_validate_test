import subprocess
import os
import csv
import argparse
import tarfile
import sys
from datetime import datetime

def run_tests(input_csv, output_html, log_dir):
    base_scenario_path = "/usr/share/gstreamer-1.0/validate/scenarios/"
    test_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_display_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # FIX: Use sys.argv[0] to get the script's filename as a string
    full_command = " ".join(sys.argv)
    script_path = sys.argv[0]
    script_name = os.path.basename(script_path)
    
    # Ensure logs are clean (no color codes)
    os.environ["GST_DEBUG_NO_COLOR"] = "1"
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    html_rows = ""
    print(f"?? Execution Started: {test_display_time}")

    try:
        with open(input_csv, mode='r', encoding='utf-8') as f_in:
            reader = csv.reader(f_in)
            for row in reader:
                if not row or row[0].startswith("#"): continue
                
                # Handling CSV rows properly
                file_name = row[0].strip()
                scenario_name = row[1].strip()
                uri = f"file:///streams/{file_name}"
                scenario_path = os.path.join(base_scenario_path, f"{scenario_name}.scenario")
                
                command = ["gst-validate-1.0", "playbin", f"uri={uri}", "flags=99", "--set-scenario", scenario_path]
                
                log_filename = f"{scenario_name}.log"
                log_path = os.path.join(log_dir, log_filename)

                print(f"Testing {scenario_name}...", end=" ", flush=True)

                # Write directly to file to ensure no logs are lost
                with open(log_path, "w") as f_log:
                    f_log.write(f"Command: {' '.join(command)}\n")
                    f_log.write("="*50 + "\n")
                    f_log.flush() 
                    
                    # Redirect stdout and stderr directly to the file stream
                    process = subprocess.run(command, stdout=f_log, stderr=subprocess.STDOUT, text=True)
                
                status = "PASS" if process.returncode == 0 else "FAIL"
                print(f"[{status}]")

                color = "#d4edda" if status == "PASS" else "#f8d7da"
                html_rows += f"""
                <tr style='background:{color};'>
                    <td style='padding:8px;'>{scenario_name}</td>
                    <td style='padding:8px;'><b>{status}</b></td>
                    <td style='padding:8px;'><a href='{log_dir}/{log_filename}'>View Log</a></td>
                </tr>"""

        # HTML Report Generation
        html_content = f"""
        <html>
        <head><style>body{{font-family:sans-serif;padding:20px;}} .cmd{{background:#eee;padding:10px;font-family:monospace;}}</style></head>
        <body>
            <h2>GstValidate Report</h2>
            <p><b>Date:</b> {test_display_time}</p>
            <p><b>Script Used:</b> <a href='{script_name}'>{script_name}</a></p>
            <p><b>Full Command:</b></p>
            <div class='cmd'>{full_command}</div>
            <br>
            <table border='1' width='100%' style='border-collapse:collapse;'>
                <tr style='background:#333; color:white;'><th>Scenario</th><th>Status</th><th>Link</th></tr>
                {html_rows}
            </table>
        </body>
        </html>"""
        
        with open(output_html, "w") as f_html:
            f_html.write(html_content)

        # Create Tarball including the script, csv, html, and log folder
        tarball_name = f"results_{test_time_str}.tgz"
        print(f"\n?? Packaging results into {tarball_name}...")
        with tarfile.open(tarball_name, "w:gz") as tar:
            tar.add(script_path, arcname=script_name)
            tar.add(input_csv)
            tar.add(output_html)
            tar.add(log_dir)
            
        print(f"? Finished! Everything saved in {tarball_name}")

    except Exception as e:
        print(f"? Critical Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GstValidate runner with packaging.")
    parser.add_argument("input", help="Path to input CSV")
    parser.add_argument("output", help="Path to output HTML report")
    parser.add_argument("log_dir", help="Directory name for individual logs")
    args = parser.parse_args()
    run_tests(args.input, args.output, args.log_dir)

