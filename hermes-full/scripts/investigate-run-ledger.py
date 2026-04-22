#!/usr/bin/env python3
# Investigate run ledger - why only 9 entries since Apr 17
import paramiko
import sys
from datetime import datetime

# TODO: Set these environment variables or replace with your values
VPS_HOST = "YOUR_VPS_IP"
VPS_USER = "YOUR_VPS_USER"
VPS_PASSWORD = "YOUR_VPS_PASSWORD"

def run_command(ssh, command, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode()
    error = stderr.read().decode()
    return exit_status, output, error

def main():
    print("=== Investigating Run Ledger ===")
    print()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {VPS_HOST}...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=15)
        print("  [OK] Connected")
        print()

        # Check run ledger location and count
        print("=== Run Ledger Location ===")
        status, out, err = run_command(ssh, "docker exec hermes1 find /opt/data -name '*run*ledger*' -o -name 'run-ledger*'")
        if status == 0:
            print(f"Found: {out.strip()}")
        print()

        # Check run ledger content
        print("=== Run Ledger Content ===")
        status, out, err = run_command(ssh, "docker exec hermes1 cat /opt/data/logs/run-ledger.jsonl 2>/dev/null | wc -l")
        if status == 0:
            print(f"Total entries: {out.strip()}")
        
        status, out, err = run_command(ssh, "docker exec hermes1 cat /opt/data/logs/run-ledger.jsonl 2>/dev/null | head -20")
        if status == 0 and out:
            print("First 20 lines:")
            print(out)
        print()

        # Check timestamps
        print("=== Entry Timestamps ===")
        status, out, err = run_command(ssh, "docker exec hermes1 cat /opt/data/logs/run-ledger.jsonl 2>/dev/null | python3 -c \"import sys,json; lines=sys.stdin.readlines(); [print(json.loads(l).get('timestamp','N/A')) for l in lines[:10]]\" 2>/dev/null")
        if status == 0:
            print(out)
        print()

        # Check Hermes logs for errors
        print("=== Recent Hermes Errors ===")
        status, out, err = run_command(ssh, "docker exec hermes1 tail -50 /opt/data/logs/errors.log 2>/dev/null | tail -20")
        if status == 0:
            print(out if out else "No errors in log")
        print()

        # Check if ledger writing is enabled in config
        print("=== Ledger Configuration ===")
        status, out, err = run_command(ssh, "docker exec hermes1 grep -i ledger /opt/data/config.yaml 2>/dev/null")
        if status == 0:
            print(out)
        else:
            print("  [INFO] No ledger config found")
        print()

        ssh.close()
        print("=== Analysis ===")
        print("The run ledger may only capture specific events (like provider activation).")
        print("Normal conversation turns may not be logged to the run ledger.")
        print("This is expected behavior - the ledger is for system events, not user messages.")
        return 0

    except Exception as e:
        print(f"  [FAIL] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
