<div align="center">

# Godot Auto Dumper

**半成品，学习中**    
**Godot 4.x 运行时 ClassDB 自动提取工具**

*自动检测 | 智能扫描 | SDK 生成*

![Python](https://img.shields.io/badge/Python-3.6+-blue?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20x64-lightgrey?style=flat-square)
![Godot](https://img.shields.io/badge/Godot-4.x-green?style=flat-square)

</div>

---

> [!CAUTION]
> **免责声明**  
> 本项目仅用于学习研究 Godot 引擎内部结构，以及在合法授权前提下的游戏 Modding/插件开发学习与验证，不得用于任何违反游戏服务条款或法律法规的行为。  
> 使用本项目产生的一切后果由使用者自行承担，作者不承担任何责任。

> [!NOTE]
> **版本兼容性说明**  
> 本项目面向 Godot 4.x（Windows x64）。Godot 3.x 版本在结构偏移与布局上存在明确差异，暂不支持。    
> 暂时只能导出C++类，不支持GDScript导出

---

## 功能概览

| 功能 | 说明 |
|:-----|:-----|
| **自动进程检测** | 通过窗口类名 `Engine` 自动发现 Godot 进程 |
| **智能 HashMap 扫描** | 使用打分算法自动定位 `ClassDB::classes` 地址 |
| **完整类信息提取** | 类名、继承关系、方法签名、属性、Variant 类型 |
| **SDK 生成** | 输出 C++ 头文件（`.hpp`）和 JSON 数据 |

---

## 打分算法

扫描 `.data` / `.bss` 段，对每个可能的 HashMap 结构打分：

| 特征 | 分数 |
|:-----|:-----|
| 类数量 500-2000 | +100 |
| 包含核心类 (Object, Node, Control...) | +50/个 |
| ClassInfo.method_map 结构有效 | +5/个 |
| ClassInfo.name 与 HashMap key 一致 | +10/个 |
| 有效元素 ≥15 | +100 |
| 有方法的类 ≥10 | +80 |

---

## 快速开始

```bash
# 1. 启动目标 Godot 游戏
# 2. 运行 dumper
python -m godot_dumper
```

### API 使用

```python
from godot_dumper import GodotDumper

dumper = GodotDumper()
dumper.auto_init()
classes = dumper.dump_classes()

# 保存文件
dumper.save_hpp("GodotSDK.hpp")
dumper.save_json("godot_classes.json")

# 获取统计
stats = dumper.get_stats()
print(f"Classes: {stats['class_count']}")
```

输出示例：

```
============================================================
Godot Auto Dumper v1.0
============================================================

[*] 搜索 Godot 进程 (窗口类名: Engine)...
[+] 目标进程: PID=15440 Title="Enter The Nyangeon"
[+] 模块: Enter The Nyangeon v 0.2.4.exe
[+] 基址: 0x7ff7e6c60000

[*] 扫描 ClassDB::classes...
[+] 找到 8 个候选:
    [0] Score=700 Offset=base+0x4ff3ca8 Size=876
        Classes: Object, Time, RefCounted...

[+] 使用: base + 0x4ff3ca8 (Score=700)

[*] 提取类信息...
[+] 共提取 875 个类
[+] 共提取 12883 个方法
[+] 共提取 4890 个属性

[+] 完成!
```

---

<details>
<summary><strong>目录结构</strong></summary>

```
godot_dumper/
├── __init__.py      # 包入口
├── __main__.py      # CLI 入口
├── constants.py     # 常量定义 (偏移、类型映射)
├── dumper.py        # 主 Dumper 类
├── generator.py     # HPP 生成
├── memory.py        # 内存读取
├── parser.py        # ClassDB 解析
├── process.py       # 进程检测
└── scanner.py       # HashMap 扫描
```

</details>

---

## 输出文件

| 文件 | 说明 |
|:-----|:-----|
| `GodotSDK.hpp` | C++ SDK 头文件，包含所有类定义、方法签名、属性偏移 |
| `godot_classes.json` | JSON 格式的完整类数据，便于二次处理 |

---

## 内存结构

<details>
<summary><strong>ClassDB::classes HashMap 结构</strong></summary>

```
ClassDB::classes (HashMap<StringName, ClassInfo>)
│
├── HashMap (48 bytes)
│   ├── +0x00: _elements (HashMapElement**)
│   ├── +0x08: _hashes (uint32_t*)
│   ├── +0x10: _head_element (链表头)
│   ├── +0x18: _tail_element (链表尾)
│   ├── +0x20: _capacity_idx
│   └── +0x24: _size
│
├── HashMapElement
│   ├── +0x00: next
│   ├── +0x08: prev
│   ├── +0x10: key (StringName._Data*)
│   └── +0x18: value (ClassInfo, inline)
│
└── ClassInfo
    ├── +0x28:  method_map (HashMap<StringName, MethodBind*>)
    ├── +0x120: property_setget (AHashMap)
    ├── +0x178: inherits (StringName)
    └── +0x180: name (StringName)
```

</details>

<details>
<summary><strong>StringName._Data 结构</strong></summary>

```
StringName._Data
├── +0x00: refcount
├── +0x04: static_count
├── +0x08: cname (const char*, 优先使用)
├── +0x10: name (UTF-32 CowData*)
├── +0x18: idx
└── +0x1C: hash
```

</details>

<details>
<summary><strong>MethodBind 结构</strong></summary>

```
MethodBind
├── +0x00: vtable
├── +0x08: method_id
├── +0x10: name (StringName._Data*)
├── +0x18: instance_class
├── +0x30: default_argument_count
├── +0x34: argument_count
├── +0x38: flags (bit0=static, bit8=const, bit16=has_return)
└── +0x40: argument_types (Variant::Type* 数组)
```

</details>

详细结构说明见：[Godot_ClassDB_Structure.md](Godot_ClassDB_Structure.md)

---

## 系统要求

- **操作系统**：Windows x64
- **Python**：3.6+
- **目标游戏**：Godot 4.x 引擎

---

## 限制

- 仅支持 Godot 4.x（3.x 结构不同）
- 字段偏移是基于类型大小的估算值，非运行时真实偏移
- 需要游戏进程正在运行

---

<div align="center">

**Platform:** Windows x64 | **License:** MIT

</div>





