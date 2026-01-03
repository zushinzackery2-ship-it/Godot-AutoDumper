"""
内存读取模块
"""

import ctypes
from ctypes import wintypes
import struct

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    wintypes.HANDLE, ctypes.c_uint64, wintypes.LPVOID,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]
ReadProcessMemory.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle


class MemoryReader:
    """跨进程内存读取器"""
    
    def __init__(self, pid: int):
        self.pid = pid
        self.handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not self.handle:
            raise Exception(f"无法打开进程 {pid}")
    
    def __del__(self):
        if hasattr(self, 'handle') and self.handle:
            CloseHandle(self.handle)
    
    def read_bytes(self, address: int, size: int) -> bytes | None:
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t()
        if not ReadProcessMemory(self.handle, address, buffer, size, ctypes.byref(bytes_read)):
            return None
        return buffer.raw[:bytes_read.value]
    
    def read_qword(self, address: int) -> int | None:
        data = self.read_bytes(address, 8)
        return struct.unpack('<Q', data)[0] if data and len(data) == 8 else None
    
    def read_dword(self, address: int) -> int | None:
        data = self.read_bytes(address, 4)
        return struct.unpack('<I', data)[0] if data and len(data) == 4 else None


def is_valid_pointer(ptr: int, base: int, module_size: int) -> bool:
    """检查是否是有效指针"""
    if ptr < 0x10000:
        return False
    if base <= ptr < base + module_size:
        return True
    if 0x10000 < ptr < 0x7FFFFFFFFFFF:
        return True
    return False


def read_cstring(reader: MemoryReader, address: int, max_len: int = 128) -> str | None:
    """读取 C 字符串"""
    if not address or address < 0x10000:
        return None
    data = reader.read_bytes(address, max_len)
    if not data:
        return None
    try:
        null_idx = data.index(0)
        s = data[:null_idx].decode('utf-8', errors='ignore')
        return s if s.isprintable() and len(s) > 0 else None
    except:
        return None


def read_stringname(reader: MemoryReader, ptr: int, base: int, module_size: int) -> str | None:
    """读取 Godot StringName"""
    if not is_valid_pointer(ptr, base, module_size):
        return None
    
    sn_data = reader.read_bytes(ptr, 32)
    if not sn_data or len(sn_data) < 24:
        return None
    
    cname_ptr = struct.unpack('<Q', sn_data[8:16])[0]
    name_ptr = struct.unpack('<Q', sn_data[16:24])[0]
    
    # 优先尝试 cname
    if is_valid_pointer(cname_ptr, base, module_size):
        name = read_cstring(reader, cname_ptr)
        if name:
            return name
    
    # 尝试 UTF-32
    if is_valid_pointer(name_ptr, base, module_size):
        utf32_data = reader.read_bytes(name_ptr, 256)
        if utf32_data:
            chars = []
            for i in range(0, len(utf32_data), 4):
                if i + 4 > len(utf32_data):
                    break
                val = struct.unpack('<I', utf32_data[i:i+4])[0]
                if val == 0:
                    break
                if val < 0x110000:
                    chars.append(chr(val))
            if chars:
                return ''.join(chars)
    return None
