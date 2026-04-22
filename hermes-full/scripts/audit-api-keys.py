#!/usr/bin/env python3
# Check API keys on VPS host and containers
import paramiko
import sys

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
    print("=== API Keys Audit ===")
    print()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {VPS_HOST}...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=15)
        print("  [OK] Connected")
        print()

        # Check VPS host .env
        print("=== VPS Host /root/.hermes/.env ===")
        status, out, err = run_command(ssh, "cat /root/.hermes/.env 2>/dev/null | grep -E '(API_KEY|TOKEN|URL)'")
        if status == 0:
            print(out)
        else:
            print("  [FAIL] File not found or no keys")
        print()

        # Check each container's .env
        containers = ['hermes1', 'hermes2', 'hermes3', 'hermes4', 'hermes5']
        for c in containers:
            print(f"=== {c} /opt/data/.env ===")
            status, out, err = run_command(ssh, f"docker exec {c} cat /opt/data/.env 2>/dev/null | grep -E '(API_KEY|TOKEN|URL)'")
            if status == 0:
                print(out if out else "  [EMPTY] No keys found")
            else:
                print("  [FAIL] File not found")
            print()

        ssh.close()
        return 0

    except Exception as e:
        print(f"  [FAIL] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
