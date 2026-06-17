"""
许可证系统
本地版激活码/机器码绑定
"""
import hashlib
import json
import time
import platform
import uuid
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("license")


@dataclass
class LicenseInfo:
    key: str
    machine_id: str
    activated_at: float
    expires_at: Optional[float]  # None = 永不过期
    license_type: str  # "permanent" / "subscription"


class LicenseManager:
    """许可证管理器"""
    
    LICENSE_FILE = Path.home() / ".lingxiao" / "license.json"
    
    # 测试用激活码（实际使用时替换为真实激活码生成逻辑）
    TEST_KEYS = {
        "LX-LOCAL-2026-ABCD": {
            "type": "permanent",
            "expires_at": None,
        },
        "LX-CLOUD-MONTHLY-2026": {
            "type": "subscription",
            "expires_at": None,  # 月卡，30天
        },
    }
    
    def __init__(self):
        self.license_info: Optional[LicenseInfo] = None
        self._load_license()
    
    def get_machine_id(self) -> str:
        """获取本机机器码"""
        # 组合多个硬件特征
        parts = [
            platform.node(),
            platform.machine(),
            platform.processor(),
            str(uuid.getnode()),  # MAC 地址
        ]
        
        raw = "-".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    
    def generate_activation_request(self) -> str:
        """生成激活请求码"""
        machine_id = self.get_machine_id()
        return f"LX-ACT-{machine_id}"
    
    def activate(self, key: str) -> bool:
        """激活许可证"""
        # 检查激活码格式
        if not key.startswith("LX-"):
            logger.error(f"无效的激活码格式: {key}")
            return False
        
        # 模拟：检查激活码是否在白名单（实际需要服务器验证）
        if key not in self.TEST_KEYS:
            logger.error(f"激活码无效: {key}")
            return False
        
        key_info = self.TEST_KEYS[key]
        
        # 生成许可证信息
        license_info = LicenseInfo(
            key=key,
            machine_id=self.get_machine_id(),
            activated_at=time.time(),
            expires_at=key_info["expires_at"],
            license_type=key_info["type"],
        )
        
        # 保存
        self._save_license(license_info)
        self.license_info = license_info
        
        logger.info(f"激活成功: {key} ({key_info['type']})")
        return True
    
    def validate(self) -> bool:
        """验证许可证是否有效"""
        if not self.license_info:
            return False
        
        # 检查是否过期
        if self.license_info.expires_at:
            if time.time() > self.license_info.expires_at:
                logger.warning("许可证已过期")
                return False
        
        # 检查机器码
        current_machine = self.get_machine_id()
        if self.license_info.machine_id != current_machine:
            logger.error("机器码不匹配，许可证无效")
            return False
        
        return True
    
    def deactivate(self) -> bool:
        """注销许可证"""
        if self.LICENSE_FILE.exists():
            self.LICENSE_FILE.unlink()
        self.license_info = None
        logger.info("许可证已注销")
        return True
    
    def get_remaining_days(self) -> Optional[int]:
        """获取剩余天数"""
        if not self.license_info or not self.license_info.expires_at:
            return None
        
        remaining = self.license_info.expires_at - time.time()
        if remaining <= 0:
            return 0
        
        return int(remaining / 86400)
    
    def _load_license(self):
        """加载许可证文件"""
        if not self.LICENSE_FILE.exists():
            return
        
        try:
            data = json.loads(self.LICENSE_FILE.read_text())
            self.license_info = LicenseInfo(
                key=data["key"],
                machine_id=data["machine_id"],
                activated_at=data["activated_at"],
                expires_at=data.get("expires_at"),
                license_type=data.get("license_type", "permanent"),
            )
            logger.info(f"已加载许可证: {self.license_info.key}")
        except Exception as e:
            logger.error(f"许可证文件读取失败: {e}")
    
    def _save_license(self, info: LicenseInfo):
        """保存许可证文件"""
        self.LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "key": info.key,
            "machine_id": info.machine_id,
            "activated_at": info.activated_at,
            "expires_at": info.expires_at,
            "license_type": info.license_type,
        }
        
        self.LICENSE_FILE.write_text(json.dumps(data, indent=2))
        logger.info(f"许可证已保存: {self.LICENSE_FILE}")
    
    def is_cloud_mode(self) -> bool:
        """检查是否为云端模式"""
        # 云端模式不需要本地许可证
        return False
    
    def get_license_status(self) -> dict:
        """获取许可证状态摘要"""
        if not self.license_info:
            return {
                "activated": False,
                "type": None,
                "remaining_days": None,
            }
        
        return {
            "activated": True,
            "key": self.license_info.key,
            "type": self.license_info.license_type,
            "remaining_days": self.get_remaining_days(),
            "valid": self.validate(),
        }


# 单例
_license_manager = None

def get_license_manager() -> LicenseManager:
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


if __name__ == "__main__":
    lm = LicenseManager()
    
    print("机器码:", lm.get_machine_id())
    print("激活请求:", lm.generate_activation_request())
    print("许可证状态:", lm.get_license_status())
    
    # 测试激活
    print("\n--- 测试激活 ---")
    if lm.activate("LX-LOCAL-2026-ABCD"):
        print("激活成功！")
        print("状态:", lm.get_license_status())
        print("有效:", lm.validate())