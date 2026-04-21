#!/usr/bin/env python3
"""
Extract only necessary VPS configs for WebUI/Hermes/KiloCode
Avoids copying entire VPS folder (15GB+)
"""

import shutil
import os
from pathlib import Path

# Define what we actually need from VPS
VPS_SOURCE = Path("C:/Users/Admin/Downloads/VPS")
TARGET = Path("G:/Github/hermes.daveai.tech/vps-configs")

# Only copy these specific config types
NEEDED_PATTERNS = [
    "**/*.yaml",
    "**/*.yml", 
    "**/*.json",
    "**/*.conf",
    "**/*.config",
    "**/*.env*",
    "**/nginx/**",
    "**/docker-compose*",
    "**/Dockerfile*",
    "**/systemd/**",
    "**/hermes/**",
    "**/webui/**",
    "**/nats/**",
    "**/postgres/**",
    "**/shiba/**",
    "**/litellm/**",
]

EXCLUDE_PATTERNS = [
    "**/*.tar.gz",
    "**/*.zip",
    "**/*.rar",
    "**/backups/**",
    "**/logs/**",
    "**/data/**",
    "**/models/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/node_modules/**",
    "**/.git/**",
]

def should_include(path: Path) -> bool:
    """Check if file should be included"""
    # Check exclusions first
    for pattern in EXCLUDE_PATTERNS:
        if path.match(pattern):
            return False
    
    # Check inclusions
    for pattern in NEEDED_PATTERNS:
        if path.match(pattern):
            return True
    
    return False

def extract_configs():
    """Extract only needed configs from VPS"""
    
    print("Extracting VPS configs for WebUI/Hermes/KiloCode...")
    print(f"Source: {VPS_SOURCE}")
    print(f"Target: {TARGET}")
    print()
    
    if not VPS_SOURCE.exists():
        print(f"! VPS source not found: {VPS_SOURCE}")
        return False
    
    TARGET.mkdir(parents=True, exist_ok=True)
    
    copied = 0
    skipped = 0
    
    for root, dirs, files in os.walk(VPS_SOURCE):
        root_path = Path(root)
        
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if not any(
            (root_path / d).match(p) for p in EXCLUDE_PATTERNS
        )]
        
        for file in files:
            src_file = root_path / file
            
            if should_include(src_file):
                # Calculate relative path
                rel_path = src_file.relative_to(VPS_SOURCE)
                dst_file = TARGET / rel_path
                
                # Create parent directories
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    shutil.copy2(src_file, dst_file)
                    copied += 1
                    if copied % 100 == 0:
                        print(f"  Copied {copied} files...")
                except Exception as e:
                    print(f"  ! Failed to copy {rel_path}: {e}")
            else:
                skipped += 1
    
    print()
    print(f"Extraction complete:")
    print(f"  Copied: {copied} config files")
    print(f"  Skipped: {skipped} non-essential files")
    print()
    print("VPS configs extracted to: vps-configs/")
    
    return True

if __name__ == "__main__":
    extract_configs()
