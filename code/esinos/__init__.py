"""ESINOS - simulateur pedagogique de systeme d'exploitation.

Le paquet reste volontairement sans dependance externe afin de pouvoir etre
execute dans un environnement de TP ordinaire.
"""

from .scheduler import Process, run_scheduler
from .memory import VirtualMemoryManager, simulate_page_replacement

__all__ = [
    "Process",
    "VirtualMemoryManager",
    "run_scheduler",
    "simulate_page_replacement",
]

__version__ = "1.0.0"
