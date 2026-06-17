# 激活码生成工具
# 用户激活时需要提供激活码

import hashlib
import time
import json
from pathlib import Path

# 机器码 → 激活码 的映射（实际使用时替换为服务端验证）
# 这里只是本地测试用

MACHINE_IDS = {
    "298F617FBC1665B2": {
        "key": "LX-LOCAL-2026-ABCD",
        "type": "permanent",
        "name": "测试机器",
    }
}


def generate_key(machine_id: str, key_type: str = "permanent") -> str:
    """生成激活码"""
    # 基于机器码生成唯一的激活码
    # 格式: LX-{TYPE}-2026-{HASH}
    timestamp = str(int(time.time()))[-6:]
    raw = f"{machine_id}-{key_type}-{timestamp}"
    hash_part = hashlib.md5(raw.encode()).hexdigest()[:8].upper()
    return f"LX-{key_type.upper()[:6]}-2026-{hash_part}"


def verify_key(machine_id: str, key: str) -> bool:
    """验证激活码"""
    if not key.startswith("LX-"):
        return False

    # 检查是否是预定义的测试码
    if key == "LX-LOCAL-2026-ABCD":
        return True

    # 检查是否是生成的码
    for mid, info in MACHINE_IDS.items():
        if mid == machine_id and info["key"] == key:
            return True

    return False


def add_machine(machine_id: str, name: str = "未知"):
    """添加一个机器到白名单"""
    key = generate_key(machine_id)
    MACHINE_IDS[machine_id] = {
        "key": key,
        "type": "permanent",
        "name": name,
    }
    print(f"机器码: {machine_id}")
    print(f"激活码: {key}")
    print(f"名称: {name}")
    return key


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--add" and len(sys.argv) > 2:
            add_machine(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "未知")
        elif sys.argv[1] == "--verify" and len(sys.argv) > 3:
            ok = verify_key(sys.argv[2], sys.argv[3])
            print(f"验证结果: {'通过' if ok else '失败'}")
        else:
            print("用法: python3 gen_key.py --add MACHINE_ID [名称]")
            print("     python3 gen_key.py --verify MACHINE_ID KEY")
    else:
        # 演示：生成当前机器的激活码
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.license import LicenseManager

        lm = LicenseManager()
        mid = lm.get_machine_id()
        key = generate_key(mid)
        print(f"当前机器码: {mid}")
        print(f"可用激活码: {key}")
        print()
        print("测试码: LX-LOCAL-2026-ABCD (任意机器)")