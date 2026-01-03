"""
ClassDB 解析模块
"""

import struct
from .memory import MemoryReader, is_valid_pointer, read_stringname
from .constants import (
    CLASSINFO_METHOD_MAP_OFFSET,
    CLASSINFO_PROP_SETGET_OFFSET,
    CLASSINFO_INHERITS_OFFSET,
    CLASSINFO_NAME_OFFSET,
    get_type_size,
)


def parse_method(reader: MemoryReader, addr: int, base: int, module_size: int) -> dict | None:
    """解析 MethodBind 结构"""
    data = reader.read_bytes(addr, 80)
    if not data:
        return None
    
    method_id = struct.unpack('<i', data[8:12])[0]
    name_ptr = struct.unpack('<Q', data[16:24])[0]
    default_arg_count = struct.unpack('<i', data[48:52])[0]
    arg_count = struct.unpack('<i', data[52:56])[0]
    flags = struct.unpack('<I', data[56:60])[0]
    arg_types_ptr = struct.unpack('<Q', data[64:72])[0]
    
    name = read_stringname(reader, name_ptr, base, module_size)
    if not name:
        return None
    
    return_type = 0
    arg_types = []
    if is_valid_pointer(arg_types_ptr, base, module_size) and 0 <= arg_count < 30:
        types_data = reader.read_bytes(arg_types_ptr, (arg_count + 1) * 4)
        if types_data and len(types_data) >= (arg_count + 1) * 4:
            return_type = struct.unpack('<i', types_data[0:4])[0]
            for i in range(arg_count):
                t = struct.unpack('<i', types_data[(i+1)*4:(i+2)*4])[0]
                arg_types.append(t)
    
    return {
        'name': name,
        'method_id': method_id,
        'arg_count': arg_count,
        'default_arg_count': default_arg_count,
        'is_static': (flags & 0x01) != 0,
        'is_const': (flags & 0x100) != 0,
        'has_return': (flags & 0x10000) != 0,
        'return_type': return_type,
        'arg_types': arg_types,
    }


def dump_class_methods(reader: MemoryReader, ci_data: bytes, base: int, module_size: int) -> list[dict]:
    """提取类的所有方法"""
    mm_head = struct.unpack('<Q', ci_data[CLASSINFO_METHOD_MAP_OFFSET+16:CLASSINFO_METHOD_MAP_OFFSET+24])[0]
    mm_size = struct.unpack('<I', ci_data[CLASSINFO_METHOD_MAP_OFFSET+36:CLASSINFO_METHOD_MAP_OFFSET+40])[0]
    
    methods = []
    current = mm_head
    count = 0
    
    while current and count < mm_size + 10:
        elem_data = reader.read_bytes(current, 32)
        if not elem_data:
            break
        next_ptr = struct.unpack('<Q', elem_data[0:8])[0]
        value_ptr = struct.unpack('<Q', elem_data[24:32])[0]
        if is_valid_pointer(value_ptr, base, module_size):
            mb = parse_method(reader, value_ptr, base, module_size)
            if mb:
                methods.append(mb)
        current = next_ptr
        count += 1
        if not next_ptr:
            break
    
    return methods


def dump_class_properties(reader: MemoryReader, ci_data: bytes, base: int, module_size: int) -> list[dict]:
    """提取类的所有属性"""
    prop_head = struct.unpack('<Q', ci_data[CLASSINFO_PROP_SETGET_OFFSET+16:CLASSINFO_PROP_SETGET_OFFSET+24])[0]
    prop_size = struct.unpack('<I', ci_data[CLASSINFO_PROP_SETGET_OFFSET+36:CLASSINFO_PROP_SETGET_OFFSET+40])[0]
    
    properties = []
    current = prop_head
    count = 0
    
    while current and count < prop_size + 10:
        elem_data = reader.read_bytes(current, 80)
        if not elem_data:
            break
        next_ptr = struct.unpack('<Q', elem_data[0:8])[0]
        key_ptr = struct.unpack('<Q', elem_data[16:24])[0]
        prop_name = read_stringname(reader, key_ptr, base, module_size)
        
        if prop_name:
            psg = elem_data[24:]
            var_type = struct.unpack('<i', psg[0:4])[0]
            properties.append({'name': prop_name, 'type': var_type})
        
        current = next_ptr
        count += 1
        if not next_ptr:
            break
    
    return properties


def dump_all_classes(reader: MemoryReader, hashmap_addr: int, base: int, module_size: int) -> dict:
    """
    提取所有类信息
    
    Returns:
        dict: {class_name: {'name', 'parent', 'methods', 'properties'}, ...}
    """
    head_element = reader.read_qword(hashmap_addr + 16)
    size = reader.read_dword(hashmap_addr + 36)
    
    if not head_element:
        return {}
    
    classes = {}
    current = head_element
    count = 0
    
    while current and count < size + 100:
        elem_data = reader.read_bytes(current, 32)
        if not elem_data:
            break
        
        next_ptr = struct.unpack('<Q', elem_data[0:8])[0]
        class_info_addr = current + 24
        
        ci_data = reader.read_bytes(class_info_addr, 0x200)
        if ci_data:
            name_ptr = struct.unpack('<Q', ci_data[CLASSINFO_NAME_OFFSET:CLASSINFO_NAME_OFFSET+8])[0]
            inherits_ptr = struct.unpack('<Q', ci_data[CLASSINFO_INHERITS_OFFSET:CLASSINFO_INHERITS_OFFSET+8])[0]
            
            class_name = read_stringname(reader, name_ptr, base, module_size)
            parent_name = read_stringname(reader, inherits_ptr, base, module_size)
            
            if class_name:
                methods = dump_class_methods(reader, ci_data, base, module_size)
                properties = dump_class_properties(reader, ci_data, base, module_size)
                classes[class_name] = {
                    'name': class_name,
                    'parent': parent_name,
                    'methods': methods,
                    'properties': properties,
                }
        
        current = next_ptr
        count += 1
        if not next_ptr:
            break
    
    return classes


def calculate_field_offsets(classes: dict) -> None:
    """计算每个类的字段偏移量（原地修改）"""
    visited = set()
    
    def get_parent_size(class_name: str) -> int:
        if class_name not in classes or class_name in visited:
            return 8
        visited.add(class_name)
        cls = classes[class_name]
        parent = cls.get('parent')
        parent_size = get_parent_size(parent) if parent else 8
        for prop in cls.get('properties', []):
            size = get_type_size(prop['type'])
            if parent_size % 8 != 0:
                parent_size = (parent_size + 7) & ~7
            parent_size += size
        visited.discard(class_name)
        return parent_size
    
    for class_name, cls in classes.items():
        parent = cls.get('parent')
        offset = get_parent_size(parent) if parent else 8
        for prop in cls.get('properties', []):
            size = get_type_size(prop['type'])
            if offset % 8 != 0:
                offset = (offset + 7) & ~7
            prop['offset'] = offset
            offset += size
        cls['size'] = offset
