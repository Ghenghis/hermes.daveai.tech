#!/usr/bin/env python3
# Create evidence ledger files under /opt/data/ledgers/
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
    print("=== Creating Evidence Ledger Files ===")
    print()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {VPS_HOST}...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=15)
        print("  [OK] Connected")
        print()

        # Create ledger directories and files in all containers
        containers = ['hermes1', 'hermes2', 'hermes3', 'hermes4', 'hermes5']
        for c in containers:
            print(f"{c}:")
            
            # Create ledger subdirectories
            ledger_dirs = ['features', 'defects', 'files', 'phases']
            for d in ledger_dirs:
                cmd = f"docker exec {c} mkdir -p /opt/data/ledgers/{d}"
                status, out, err = run_command(ssh, cmd)
                if status == 0:
                    print(f"  [OK] Created /opt/data/ledgers/{d}")
                else:
                    print(f"  [WARN] Failed to create {d}: {err}")
            
            # Create empty ledger files
            ledger_files = [
                '/opt/data/ledgers/features.jsonl',
                '/opt/data/ledgers/defects.jsonl',
                '/opt/data/ledgers/files.jsonl',
                '/opt/data/ledgers/phases.jsonl'
            ]
            for f in ledger_files:
                cmd = f"docker exec {c} touch {f}"
                status, out, err = run_command(ssh, cmd)
                if status == 0:
                    print(f"  [OK] Created {f}")
                else:
                    print(f"  [WARN] Failed to create {f}: {err}")
            print()

        # Verify
        print("=== Verification ===")
        status, out, err = run_command(ssh, "docker exec hermes1 ls -la /opt/data/ledgers/")
        if status == 0:
            print("hermes1 ledgers:")
            print(out)
        print()

        ssh.close()
        print("=== Complete ===")
        return 0

    except Exception as e:
        print(f"  [FAIL] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
