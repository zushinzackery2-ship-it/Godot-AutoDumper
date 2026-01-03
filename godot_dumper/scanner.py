"""
ClassDB HashMap 扫描模块
"""

import struct
from .memory import MemoryReader, is_valid_pointer, read_stringname

# Godot 核心类列表，用于打分
GODOT_CORE_CLASSES = {
    'Object', 'RefCounted', 'Resource', 'Node', 'Node2D', 'Node3D',
    'Control', 'Sprite2D', 'Camera2D', 'Camera3D', 'AudioStreamPlayer'
}


def score_hashmap(reader: MemoryReader, addr: int, base: int, module_size: int) -> tuple[int, dict]:
    """
    对 HashMap 结构打分 - ClassDB 特征检测
    
    Returns:
        tuple: (score, details_dict)
    """
    data = reader.read_bytes(addr, 48)
    if not data or len(data) < 48:
        return 0, {}
    
    elements_ptr = struct.unpack('<Q', data[0:8])[0]
    hashes_ptr = struct.unpack('<Q', data[8:16])[0]
    head_ptr = struct.unpack('<Q', data[16:24])[0]
    tail_ptr = struct.unpack('<Q', data[24:32])[0]
    capacity_idx = struct.unpack('<I', data[32:36])[0]
    size = struct.unpack('<I', data[36:40])[0]
    
    score = 0
    details = {'size': size, 'head_ptr': hex(head_ptr)}
    
    # 基本结构验证
    if size < 10 or size > 10000:
        return 0, details
    if not (0 < capacity_idx < 30):
        return 0, details
    if not is_valid_pointer(head_ptr, base, module_size):
        return 0, details
    if not is_valid_pointer(tail_ptr, base, module_size):
        return 0, details
    
    # ClassDB 特征: 类数量通常 500-2000
    if 500 <= size <= 2000:
        score += 100
    elif 200 <= size <= 3000:
        score += 50
    else:
        score += 10
    
    # 遍历链表深度验证
    valid_elements = 0
    has_methods = 0
    class_names = []
    current = head_ptr
    
    for i in range(min(20, size)):
        if not current:
            break
        elem_data = reader.read_bytes(current, 32)
        if not elem_data:
            break
        
        next_ptr = struct.unpack('<Q', elem_data[0:8])[0]
        prev_ptr = struct.unpack('<Q', elem_data[8:16])[0]
        key_ptr = struct.unpack('<Q', elem_data[16:24])[0]
        
        # 链表完整性检查
        if i == 0 and prev_ptr != 0:
            score -= 20
        
        name = read_stringname(reader, key_ptr, base, module_size)
        if name and len(name) > 0:
            # 类名格式检查
            if name[0].isupper() and name.replace('_', '').replace('2D', '').replace('3D', '').isalnum():
                valid_elements += 1
                class_names.append(name)
                
                # Godot 核心类加分
                if name in GODOT_CORE_CLASSES:
                    score += 50
                
                # 检查 ClassInfo 结构
                class_info_addr = current + 24
                ci_data = reader.read_bytes(class_info_addr, 0x190)
                if ci_data:
                    # 验证 method_map (+0x28)
                    mm_head = struct.unpack('<Q', ci_data[0x28+16:0x28+24])[0]
                    mm_size = struct.unpack('<I', ci_data[0x28+36:0x28+40])[0]
                    if is_valid_pointer(mm_head, base, module_size) and 0 < mm_size < 1000:
                        has_methods += 1
                        score += 5
                    
                    # 验证 name (+0x180) 与 key 一致
                    name_ptr = struct.unpack('<Q', ci_data[0x180:0x188])[0]
                    ci_name = read_stringname(reader, name_ptr, base, module_size)
                    if ci_name == name:
                        score += 10
        
        current = next_ptr
        if not current:
            break
    
    # 有效元素比例
    if valid_elements >= 15:
        score += 100
    elif valid_elements >= 10:
        score += 50
    else:
        score += valid_elements * 3
    
    # 有方法的类比例
    if has_methods >= 10:
        score += 80
    elif has_methods >= 5:
        score += 40
    
    details['valid_elements'] = valid_elements
    details['has_methods'] = has_methods
    details['sample_names'] = class_names[:5]
    
    return score, details


def scan_for_classdb(reader: MemoryReader, base: int, module_size: int, sections: list[dict]) -> list[dict]:
    """
    扫描数据段寻找 ClassDB::classes
    
    Returns:
        list of dict: 候选列表，按分数降序排列
    """
    candidates = []
    
    # 筛选数据段
    data_sections = [
        s for s in sections 
        if 'data' in s['name'].lower() or 'bss' in s['name'].lower()
    ]
    if not data_sections:
        data_sections = [{'va': base, 'size': module_size, 'name': 'full'}]
    
    for sec in data_sections:
        start = sec['va']
        end = start + sec['size']
        addr = start
        
        while addr < end - 48:
            score, details = score_hashmap(reader, addr, base, module_size)
            if score > 100:
                candidates.append({
                    'address': addr,
                    'offset': addr - base,
                    'score': score,
                    'details': details,
                })
            addr += 8
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates
