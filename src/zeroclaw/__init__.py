"""
ZeroClaw Package - ZeroClaw gateway and adapters
"""

from .adapters import (
    ZeroClawGateway,
    GitAdapter,
    ShellAdapter,
    FilesystemAdapter,
    ResearchAdapter,
)

__all__ = [
    "ZeroClawGateway",
    "GitAdapter",
    "ShellAdapter",
    "FilesystemAdapter",
    "ResearchAdapter",
]
