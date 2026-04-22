#!/usr/bin/env python3
# Configure Tirith shell hook in all containers
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
    print("=== Configuring Tirith Shell Hook ===")
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
            print(f"{c}:")
            # Check if Tirith binary exists at known location
            status, out, err = run_command(ssh, f"docker exec {c} ls -la /opt/data/bin/tirith")
            if status == 0:
                print("  [OK] Tirith found at /opt/data/bin/tirith")
                
                # Add hook to .bashrc with full path
                cmd = f"docker exec {c} bash -c 'grep -q \"tirith init\" ~/.bashrc || echo \"eval $(/opt/data/bin/tirith init --shell bash)\" >> ~/.bashrc'"
                status, out, err = run_command(ssh, cmd)
                if status == 0:
                    print("  [OK] Added hook to ~/.bashrc")
                else:
                    print(f"  [WARN] Failed to add hook: {err}")
            else:
                print("  [WARN] Tirith not found at /opt/data/bin/tirith")
            print()

        ssh.close()
        print("=== Complete ===")
        print("Note: Shell hooks require container restart to take effect")
        return 0

    except Exception as e:
        print(f"  [FAIL] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
