#!/usr/bin/env python3
# Check Discord slash command configuration and fix 8KB limit
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
    print("=== Discord Slash Command 8KB Limit Fix ===")
    print()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {VPS_HOST}...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=15)
        print("  [OK] Connected")
        print()

        # Check Hermes config for Discord settings
        print("=== Checking Hermes Config ===")
        status, out, err = run_command(ssh, "docker exec hermes1 cat /opt/data/config.yaml 2>/dev/null | head -50")
        if status == 0:
            print(out)
        print()

        # Check if there's a Discord-specific config
        print("=== Checking Discord Config ===")
        status, out, err = run_command(ssh, "docker exec hermes1 ls -la /opt/data/ | grep -i discord")
        if status == 0:
            print(out)
        else:
            print("  [INFO] No Discord-specific config file found")
        print()

        # Check skills count
        print("=== Skills Count ===")
        status, out, err = run_command(ssh, "docker exec hermes1 find /opt/data/skills -name 'SKILL.md' 2>/dev/null | wc -l")
        if status == 0:
            print(f"  External skills: {out.strip()}")
        status, out, err = run_command(ssh, "docker exec hermes1 find /opt/hermes/skills -name 'SKILL.md' 2>/dev/null | wc -l")
        if status == 0:
            print(f"  Bundled skills: {out.strip()}")
        print()

        ssh.close()
        print("=== Next Steps ===")
        print("To fix Discord 8KB limit, options:")
        print("1. Disable slash commands for skills (use message-based only)")
        print("2. Configure Hermes to exclude certain skills from slash registration")
        print("3. Split skills into command groups")
        print()
        print("This requires modifying Hermes config.yaml or Discord platform settings.")
        print()
        return 0

    except Exception as e:
        print(f"  [FAIL] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
