"""DialBB multimodal client package."""

__version__ = "1.2.0"

# Core engine exports
from .core import CoreDialogueEngine, DialogueEvent
from .engine import DialogueEngineManager, Settings, DialogueSession

__all__ = [
    "CoreDialogueEngine",
    "DialogueEvent",
    "DialogueEngineManager",
    "Settings",
    "DialogueSession",
]
