#!/usr/bin/env python3
# Phase 4: gh auth token push to VPS containers (Python paramiko approach)
import paramiko
import sys

GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"
VPS_HOST = "YOUR_VPS_IP"
VPS_USER = "YOUR_VPS_USER"
VPS_PASSWORD = "YOUR_VPS_PASSWORD"

def main():
    print("=== Phase 4: Push gh token to VPS containers (paramiko) ===")
    print(f"Token: {GITHUB_TOKEN[:20]}...")
    print()

    try:
        # Connect to VPS
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {VPS_HOST}...")
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=15)
        print("  [OK] Connected to VPS")
        print()

        # Push token to VPS
        print("Pushing token to VPS...")
        sftp = ssh.open_sftp()
        with sftp.file('/tmp/gh-token.txt', 'w') as f:
            f.write(GITHUB_TOKEN)
        sftp.chmod('/tmp/gh-token.txt', 0o600)
        sftp.close()
        print("  [OK] Token pushed to /tmp/gh-token.txt")
        print()

        # Authenticate gh in all 5 containers
        print("Authenticating gh in containers...")
        containers = ['hermes1', 'hermes2', 'hermes3', 'hermes4', 'hermes5']
        for c in containers:
            print(f"  {c}:", end=' ')
            # Read token and pipe to gh auth
            stdin, stdout, stderr = ssh.exec_command(
                f"cat /tmp/gh-token.txt | docker exec -i {c} bash -c 'gh auth login --with-token'",
                timeout=30
            )
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                # Check gh auth status
                stdin2, stdout2, stderr2 = ssh.exec_command(
                    f"docker exec {c} gh auth status 2>&1 | head -2",
                    timeout=10
                )
                status = stdout2.read().decode().strip()
                print(f"[OK] {status.split(chr(10))[0] if chr(10) in status else status}")
            else:
                print(f"[FAIL] exit {exit_status}")
        print()

        # Cleanup
        print("Cleaning up...")
        ssh.exec_command("rm /tmp/gh-token.txt")
        print("  [OK] Removed /tmp/gh-token.txt")
        print()

        ssh.close()
        print("=== Phase 4 COMPLETE ===")
        return 0

    except Exception as e:
        print(f"  [FAIL] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
