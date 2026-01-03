"""
主 Dumper 类
"""

import json
from .memory import MemoryReader
from .process import find_godot_process, get_module_info, get_pe_sections
from .scanner import scan_for_classdb
from .parser import dump_all_classes, calculate_field_offsets
from .generator import generate_hpp


class GodotDumper:
    """Godot ClassDB Dumper"""
    
    def __init__(self):
        self.pid: int | None = None
        self.title: str | None = None
        self.module_name: str | None = None
        self.base: int | None = None
        self.module_size: int | None = None
        self.reader: MemoryReader | None = None
        self.sections: list[dict] = []
        self.classdb_addr: int | None = None
        self.classdb_offset: int | None = None
        self.classes: dict = {}
    
    def auto_init(self, process_index: int = 0) -> bool:
        """
        自动初始化：检测进程、扫描 ClassDB
        
        Args:
            process_index: 当有多个 Godot 进程时选择哪个
            
        Returns:
            bool: 是否成功
        """
        # 查找进程
        processes = find_godot_process()
        if not processes:
            print("[-] 未找到 Godot 进程")
            return False
        
        if process_index >= len(processes):
            process_index = 0
        
        proc = processes[process_index]
        self.pid = proc['pid']
        self.title = proc['title']
        
        # 获取模块信息
        self.module_name, self.base, self.module_size = get_module_info(self.pid)
        if not self.base:
            print("[-] 无法获取模块信息")
            return False
        
        # 创建内存读取器
        self.reader = MemoryReader(self.pid)
        
        # 获取 PE 段
        self.sections = get_pe_sections(self.reader, self.base)
        
        # 扫描 ClassDB
        candidates = scan_for_classdb(self.reader, self.base, self.module_size, self.sections)
        if not candidates:
            print("[-] 未找到 ClassDB::classes")
            return False
        
        # 自动选择包含 Object 的
        selected = None
        for c in candidates:
            names = c['details'].get('sample_names', [])
            if 'Object' in names:
                selected = c
                break
        
        if not selected:
            selected = candidates[0]
        
        self.classdb_addr = selected['address']
        self.classdb_offset = selected['offset']
        
        return True
    
    def dump_classes(self) -> dict:
        """
        提取所有类信息
        
        Returns:
            dict: 类信息字典
        """
        if not self.reader or not self.classdb_addr:
            raise RuntimeError("请先调用 auto_init()")
        
        self.classes = dump_all_classes(
            self.reader, self.classdb_addr, self.base, self.module_size
        )
        calculate_field_offsets(self.classes)
        return self.classes
    
    def save_json(self, path: str) -> None:
        """保存为 JSON 文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.classes, f, indent=2, ensure_ascii=False)
    
    def save_hpp(self, path: str) -> None:
        """保存为 C++ 头文件"""
        content = generate_hpp(self.classes)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'class_count': len(self.classes),
            'method_count': sum(len(c['methods']) for c in self.classes.values()),
            'property_count': sum(len(c['properties']) for c in self.classes.values()),
        }
