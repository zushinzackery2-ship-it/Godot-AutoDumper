"""
Godot Auto Dumper
=================
Automatically dump ClassDB from running Godot 4.x games.

Usage:
    from godot_dumper import GodotDumper
    
    dumper = GodotDumper()
    dumper.auto_init()
    classes = dumper.dump_classes()
    dumper.save_hpp("GodotSDK.hpp")
"""

from .dumper import GodotDumper
from .memory import MemoryReader
from .process import find_godot_process, get_module_info
from .scanner import scan_for_classdb
from .parser import dump_all_classes
from .generator import generate_hpp

__version__ = "1.0.0"
__all__ = [
    "GodotDumper",
    "MemoryReader", 
    "find_godot_process",
    "get_module_info",
    "scan_for_classdb",
    "dump_all_classes",
    "generate_hpp",
]
