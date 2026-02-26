import subprocess
import os
import csv
import argparse
import tarfile
import sys
from datetime import datetime

def run_tests(input_csv, output_html, log_dir):
    # GStreamer scenario base path
    base_scenario_path = "/usr/share/gstreamer-1.0/validate/scenarios/"
    test_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_display_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    script_path = sys.argv[0]
    script_name = os.path.basename(script_path)
    full_command = " ".join(sys.argv)
    
    # Statistics
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    timeout_tests = 0
    
    os.environ["GST_DEBUG_NO_COLOR"] = "1"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    html_rows = ""
    print(f"🚀 Execution Started: {test_display_time} (Timeout: 10m per test)")

    try:
        with open(input_csv, mode='r', encoding='utf-8') as f_in:
            reader = csv.reader(f_in)
            for row in reader:
                if not row or row[0].startswith("#"): continue
                
                total_tests += 1
                file_name = row[0].strip()
                scenario_name = row[1].strip() if len(row) > 1 else row[0].strip()
                
                uri = f"file:///streams/{file_name}"
                scenario_path = os.path.join(base_scenario_path, f"{scenario_name}.scenario")
                command = ["gst-validate-1.0", "playbin", f"uri={uri}", "flags=99", "--set-scenario", scenario_path]
                
                log_filename = f"{scenario_name}.log"
                log_path = os.path.join(log_dir, log_filename)

                print(f"[{total_tests}] Testing {scenario_name}...", end=" ", flush=True)

                status = "UNKNOWN"
                exit_code = "N/A"

                # Open log file and run command with 600s (10 min) timeout
                with open(log_path, "w") as f_log:
                    f_log.write(f"Command: {' '.join(command)}\n" + "="*50 + "\n")
                    f_log.flush()
                    
                    try:
                        # MAJOR CHANGE: timeout=600 (10 minutes)
                        process = subprocess.run(command, stdout=f_log, stderr=subprocess.STDOUT, text=True, timeout=600)
                        
                        if process.returncode == 0:
                            status = "PASS"
                            passed_tests += 1
                        else:
                            status = "FAIL"
                            failed_tests += 1
                        exit_code = process.returncode
                        
                    except subprocess.TimeoutExpired as e:
                        # Handle Timeout
                        status = "TIMEOUT"
                        timeout_tests += 1
                        exit_code = "KILLED"
                        f_log.write(f"\n\n[!!!] TEST TIMEOUT EXCEEDED (10 MINUTES) - KILLED BY SCRIPT\n")
                        if e.stdout: f_log.write(e.stdout.decode())
                        if e.stderr: f_log.write(e.stderr.decode())
                
                print(f"[{status}]")

                # HTML Formatting
                color = "#d4edda" if status == "PASS" else ("#fff3cd" if status == "TIMEOUT" else "#f8d7da")
                html_rows += f"""
                <tr style='background:{color};'>
                    <td style='padding:8px; border:1px solid #ddd;'>{scenario_name}</td>
                    <td style='padding:8px; border:1px solid #ddd;'>{file_name}</td>
                    <td style='padding:8px; border:1px solid #ddd; text-align:center;'><b>{status}</b></td>
                    <td style='padding:8px; border:1px solid #ddd; text-align:center;'>
                        <a href='{log_dir}/{log_filename}' target='_blank'>View Log</a> ({exit_code})
                    </td>
                </tr>"""

        # Calculate Results
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Generate HTML
        html_content = f"""
        <html>
        <head><style>
            body{{font-family:sans-serif;padding:20px;background:#f9f9f9;}}
            .summary{{background:#fff;padding:15px;border:1px solid #ccc;border-radius:5px;margin-bottom:20px;display:inline-block;}}
            .cmd{{background:#eee;padding:10px;font-family:monospace;font-size:0.9em;}}
            table{{border-collapse:collapse; width:100%; background:#fff;}}
            th{{background:#333; color:white; padding:10px;}}
        </style></head>
        <body>
            <h2>GstValidate Execution Report</h2>
            <div class="summary">
                <b>Summary:</b> Total {total_tests} | 
                <span style="color:green;">Pass: {passed_tests}</span> | 
                <span style="color:red;">Fail: {failed_tests}</span> | 
                <span style="color:orange;">Timeout: {timeout_tests}</span><br>
                <b>Success Rate: {pass_rate:.1f}%</b>
            </div>
            <p><b>Date:</b> {test_display_time}</p>
            <p><b>Script:</b> <a href='{script_name}'>{script_name}</a></p>
            <p><b>Command:</b> <div class='cmd'>{full_command}</div></p>
            <table border='1'>
                <tr><th>Scenario</th><th>File</th><th>Status</th><th>Log Link</th></tr>
                {html_rows}
            </table>
        </body>
        </html>"""
        
        with open(output_html, "w") as f_html:
            f_html.write(html_content)

        # Create TGZ Tarball
        tarball_name = f"results_{test_time_str}.tgz"
        with tarfile.open(tarball_name, "w:gz") as tar:
            tar.add(script_path, arcname=script_name)
            tar.add(input_csv)
            tar.add(output_html)
            tar.add(log_dir)
            
        print(f"\n✅ Done! Result: {passed_tests}/{total_tests} Passed ({timeout_tests} Timed out).")
        print(f"📦 Package: {os.path.abspath(tarball_name)}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="CSV input")
    parser.add_argument("output", help="HTML report")
    parser.add_argument("log_dir", help="Log folder")
    args = parser.parse_args()
    run_tests(args.input, args.output, args.log_dir)

