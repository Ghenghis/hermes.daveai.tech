#!/usr/bin/env python3
# Check and fix gh CLI auth in all containers
import paramiko
import sys

VPS_HOST = "YOUR_VPS_IP"
VPS_USER = "YOUR_VPS_USER"
VPS_PASSWORD = "YOUR_VPS_PASSWORD"
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"

def run_command(ssh, command, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode()
    error = stderr.read().decode()
    return exit_status, output, error

def main():
    print("=== Checking gh CLI Auth Status ===")
    print()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {VPS_HOST}...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=15)
        print("  [OK] Connected")
        print()

        # Check each container's gh auth status
        containers = ['hermes1', 'hermes2', 'hermes3', 'hermes4', 'hermes5']
        for c in containers:
            print(f"{c} gh auth status:")
            status, out, err = run_command(ssh, f"docker exec {c} gh auth status 2>&1 | head -3")
            if status == 0:
                print(f"  {out.strip()}")
            else:
                print(f"  [FAIL] {err.strip()}")
        print()

        # Re-authenticate all containers
        print("=== Re-authenticating gh CLI ===")
        # Push token to VPS
        cmd = f"echo '{GITHUB_TOKEN}' > /tmp/gh-token.txt"
        run_command(ssh, cmd)
        print("  [OK] Token pushed to VPS")
        print()

        for c in containers:
            print(f"  {c}:", end=' ')
            cmd = f"cat /tmp/gh-token.txt | docker exec -i {c} bash -c 'gh auth login --with-token'"
            status, out, err = run_command(ssh, cmd, timeout=30)
            if status == 0:
                print("[OK]")
            else:
                print(f"[FAIL] {err}")
        print()

        # Verify
        print("=== Verification ===")
        for c in containers:
            status, out, err = run_command(ssh, f"docker exec {c} gh auth status 2>&1 | head -1")
            if status == 0:
                print(f"  {c}: {out.strip()}")
            else:
                print(f"  {c}: [FAIL]")
        print()

        # Cleanup
        run_command(ssh, "rm /tmp/gh-token.txt")
        print("  [OK] Cleanup complete")
        print()

        ssh.close()
        print("=== Complete ===")
        return 0

    except Exception as e:
        print(f"  [FAIL] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
