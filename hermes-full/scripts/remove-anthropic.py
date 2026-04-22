#!/usr/bin/env python3
# Remove Anthropic API, configure MiniMax HighSpeed 2.7
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
    print("=== Removing Anthropic API, Configuring MiniMax HighSpeed 2.7 ===")
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
            # Remove ANTHROPIC_API_KEY
            cmd = f"docker exec {c} sed -i '/ANTHROPIC_API_KEY/d' /opt/data/.env"
            status, out, err = run_command(ssh, cmd)
            if status == 0:
                print("  [OK] Removed ANTHROPIC_API_KEY")
            else:
                print(f"  [WARN] Failed to remove: {err}")

            # Ensure MINIMAX_API_KEY and BASE_URL are present
            minimax_key = "YOUR_MINIMAX_API_KEY"  # Get from https://platform.minimaxi.chat
            minimax_url = "https://api.minimaxi.chat/v1"

            cmd = f"docker exec {c} grep -q 'MINIMAX_API_KEY' /opt/data/.env || echo 'MINIMAX_API_KEY={minimax_key}' >> /opt/data/.env"
            run_command(ssh, cmd)

            cmd = f"docker exec {c} grep -q 'MINIMAX_BASE_URL' /opt/data/.env || echo 'MINIMAX_BASE_URL={minimax_url}' >> /opt/data/.env"
            run_command(ssh, cmd)

            print("  [OK] MiniMax configured")
            print()

        # Verify
        print("=== Verification ===")
        for c in containers:
            status, out, err = run_command(ssh, f"docker exec {c} grep -E '(ANTHROPIC|MINIMAX)' /opt/data/.env")
            print(f"{c}:")
            if out:
                print(f"  {out.strip()}")
            else:
                print("  [EMPTY]")
            print()

        ssh.close()
        print("=== Complete ===")
        return 0

    except Exception as e:
        print(f"  [FAIL] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
