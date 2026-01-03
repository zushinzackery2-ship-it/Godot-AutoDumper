"""
命令行入口
python -m godot_dumper
"""

from .dumper import GodotDumper
from .process import find_godot_process


def main():
    print("=" * 60)
    print("Godot Auto Dumper v1.0")
    print("=" * 60)
    
    # 1. 查找进程
    print("\n[*] 搜索 Godot 进程 (窗口类名: Engine)...")
    processes = find_godot_process()
    
    if not processes:
        print("[-] 未找到 Godot 进程")
        print("    请确保游戏正在运行")
        return
    
    # 多进程选择
    process_index = 0
    if len(processes) > 1:
        print(f"[!] 找到 {len(processes)} 个 Godot 进程:")
        for i, p in enumerate(processes):
            print(f"    [{i}] PID={p['pid']} Title=\"{p['title']}\"")
        process_index = int(input("选择进程 [0]: ") or "0")
    
    # 2. 初始化
    dumper = GodotDumper()
    if not dumper.auto_init(process_index):
        return
    
    print(f"[+] 目标进程: PID={dumper.pid} Title=\"{dumper.title}\"")
    print(f"[+] 模块: {dumper.module_name}")
    print(f"[+] 基址: {hex(dumper.base)}")
    print(f"[+] 大小: {hex(dumper.module_size)}")
    
    print(f"\n[+] PE 段:")
    for sec in dumper.sections:
        print(f"    {sec['name']}: {hex(sec['va'])} size={hex(sec['size'])}")
    
    print(f"\n[+] ClassDB: base + {hex(dumper.classdb_offset)}")
    
    # 3. 提取类
    print(f"\n[*] 提取类信息...")
    classes = dumper.dump_classes()
    
    stats = dumper.get_stats()
    print(f"[+] 共提取 {stats['class_count']} 个类")
    print(f"[+] 共提取 {stats['method_count']} 个方法")
    print(f"[+] 共提取 {stats['property_count']} 个属性")
    
    # 4. 保存
    print(f"\n[*] 保存文件...")
    dumper.save_json('godot_classes.json')
    print(f"[+] godot_classes.json")
    
    dumper.save_hpp('GodotSDK.hpp')
    print(f"[+] GodotSDK.hpp")
    
    # 5. 统计
    print(f"\n[*] Top 10 类 (按方法数):")
    top_classes = sorted(classes.items(), key=lambda x: len(x[1]['methods']), reverse=True)[:10]
    for name, cls in top_classes:
        print(f"    {name}: {len(cls['methods'])} methods, {len(cls['properties'])} properties")
    
    print(f"\n[+] 完成!")


if __name__ == "__main__":
    main()
