#!/usr/bin/env python3
# Restart all 5 Hermes containers to apply API key changes
import paramiko
import sys
import time

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
    print("=== Restarting Hermes Containers ===")
    print()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {VPS_HOST}...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=15)
        print("  [OK] Connected")
        print()

        containers = ['hermes1', 'hermes2', 'hermes3', 'hermes4', 'hermes5']
        for c in containers:
            print(f"Restarting {c}...")
            cmd = f"docker restart {c}"
            status, out, err = run_command(ssh, cmd, timeout=60)
            if status == 0:
                print(f"  [OK] {c} restarted")
            else:
                print(f"  [FAIL] {c}: {err}")
            time.sleep(2)
        print()

        # Wait for containers to be healthy
        print("Waiting for containers to be healthy...")
        time.sleep(10)
        print()

        # Check status
        print("=== Container Status ===")
        for c in containers:
            cmd = f"docker ps --filter name={c} --format '{{{{.Status}}}}'"
            status, out, err = run_command(ssh, cmd)
            if out:
                print(f"  {c}: {out.strip()}")
        print()

        ssh.close()
        print("=== Complete ===")
        return 0

    except Exception as e:
        print(f"  [FAIL] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
