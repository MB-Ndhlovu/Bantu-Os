"""
Application context for the CLI, holding Kernel, AgentManager, and Memory.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bantu_os.core.kernel.kernel import Kernel
from bantu_os.agents.agent_manager import AgentManager
from bantu_os.memory.memory import Memory


@dataclass
class AppContext:
    kernel: Kernel
    agent_manager: AgentManager
    memory: Optional[Memory] = None
