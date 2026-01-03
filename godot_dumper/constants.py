"""
常量定义
"""

# ClassInfo 结构偏移
CLASSINFO_METHOD_MAP_OFFSET = 0x28
CLASSINFO_PROP_SETGET_OFFSET = 0x120
CLASSINFO_INHERITS_OFFSET = 0x178
CLASSINFO_NAME_OFFSET = 0x180

# Variant::Type 到 C++ 类型映射
VARIANT_TO_CPP = {
    0: "Variant",
    1: "bool",
    2: "int64_t",
    3: "double",
    4: "String",
    5: "Vector2",
    6: "Vector2i",
    7: "Rect2",
    8: "Rect2i",
    9: "Vector3",
    10: "Vector3i",
    11: "Transform2D",
    12: "Vector4",
    13: "Vector4i",
    14: "Plane",
    15: "Quaternion",
    16: "AABB",
    17: "Basis",
    18: "Transform3D",
    19: "Projection",
    20: "Color",
    21: "StringName",
    22: "NodePath",
    23: "RID",
    24: "Object*",
    25: "Callable",
    26: "Signal",
    27: "Dictionary",
    28: "Array",
    29: "PackedByteArray",
    30: "PackedInt32Array",
    31: "PackedInt64Array",
    32: "PackedFloat32Array",
    33: "PackedFloat64Array",
    34: "PackedStringArray",
    35: "PackedVector2Array",
    36: "PackedVector3Array",
    37: "PackedColorArray",
    38: "PackedVector4Array",
}

# 类型大小 (用于计算偏移)
TYPE_SIZES = {
    0: 24,   # Variant
    1: 1,    # bool
    2: 8,    # int64_t
    3: 8,    # double
    4: 8,    # String (指针)
    5: 8,    # Vector2
    6: 8,    # Vector2i
    7: 16,   # Rect2
    8: 16,   # Rect2i
    9: 12,   # Vector3
    10: 12,  # Vector3i
    11: 24,  # Transform2D
    12: 16,  # Vector4
    13: 16,  # Vector4i
    14: 16,  # Plane
    15: 16,  # Quaternion
    16: 24,  # AABB
    17: 36,  # Basis
    18: 48,  # Transform3D
    19: 64,  # Projection
    20: 16,  # Color
    21: 8,   # StringName
    22: 8,   # NodePath
    23: 8,   # RID
    24: 8,   # Object*
    25: 16,  # Callable
    26: 16,  # Signal
    27: 8,   # Dictionary
    28: 8,   # Array
}


def get_cpp_type(type_id: int) -> str:
    """获取 C++ 类型名"""
    return VARIANT_TO_CPP.get(type_id, "Variant")


def get_type_size(type_id: int) -> int:
    """获取类型大小"""
    return TYPE_SIZES.get(type_id, 8)
