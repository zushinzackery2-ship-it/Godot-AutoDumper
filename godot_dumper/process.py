"""
进程检测模块
"""

import ctypes
from ctypes import wintypes
import struct
import subprocess

user32 = ctypes.WinDLL('user32', use_last_error=True)

EnumWindows = user32.EnumWindows
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetClassName = user32.GetClassNameW
GetWindowText = user32.GetWindowTextW

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def find_godot_process() -> list[dict]:
    """
    通过窗口类名 'Engine' 查找 Godot 进程
    
    Returns:
        list of dict: [{'pid': int, 'hwnd': int, 'title': str}, ...]
    """
    results = []
    
    def enum_callback(hwnd, lparam):
        class_name = ctypes.create_unicode_buffer(256)
        title = ctypes.create_unicode_buffer(256)
        GetClassName(hwnd, class_name, 256)
        GetWindowText(hwnd, title, 256)
        
        if class_name.value == "Engine":
            pid = wintypes.DWORD()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            results.append({
                'pid': pid.value,
                'hwnd': hwnd,
                'title': title.value,
            })
        return True
    
    EnumWindows(WNDENUMPROC(enum_callback), 0)
    return results


def get_module_info(pid: int) -> tuple[str | None, int | None, int | None]:
    """
    获取主模块信息
    
    Returns:
        tuple: (module_name, base_address, module_size)
    """
    try:
        cmd = (
            f"Get-Process -Id {pid} | "
            "Select-Object -ExpandProperty MainModule | "
            "ForEach-Object { $_.ModuleName + '|' + $_.BaseAddress.ToString() + '|' + $_.ModuleMemorySize.ToString() }"
        )
        output = subprocess.check_output(
            ['powershell', '-Command', cmd],
            encoding='utf-8', errors='ignore'
        )
        parts = output.strip().split('|')
        if len(parts) == 3:
            return parts[0], int(parts[1]), int(parts[2])
    except:
        pass
    return None, None, None


def get_pe_sections(reader, base: int) -> list[dict]:
    """
    解析 PE 头获取段信息
    
    Returns:
        list of dict: [{'name': str, 'va': int, 'size': int}, ...]
    """
    dos_header = reader.read_bytes(base, 64)
    if not dos_header or dos_header[:2] != b'MZ':
        return []
    
    e_lfanew = struct.unpack('<I', dos_header[60:64])[0]
    pe_header = reader.read_bytes(base + e_lfanew, 264)
    if not pe_header or pe_header[:4] != b'PE\x00\x00':
        return []
    
    num_sections = struct.unpack('<H', pe_header[6:8])[0]
    size_opt_header = struct.unpack('<H', pe_header[20:22])[0]
    
    sections = []
    section_offset = e_lfanew + 24 + size_opt_header
    
    for i in range(num_sections):
        sec_data = reader.read_bytes(base + section_offset + i * 40, 40)
        if not sec_data:
            continue
        
        name = sec_data[:8].rstrip(b'\x00').decode('ascii', errors='ignore')
        virtual_size = struct.unpack('<I', sec_data[8:12])[0]
        virtual_addr = struct.unpack('<I', sec_data[12:16])[0]
        
        sections.append({
            'name': name,
            'va': base + virtual_addr,
            'size': virtual_size,
        })
    
    return sections
