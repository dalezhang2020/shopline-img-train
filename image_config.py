"""
Configuration for image augmentation task
"""
from pydantic_settings import BaseSettings
from typing import Optional


class ImageAugmentationSettings(BaseSettings):
    """Image augmentation settings"""

    # MySQL Database Configuration
    database_host: str = "am-bp1ch634s7l1264ft167320o.ads.aliyuncs.com"
    database_user: str = "dale_admin"
    database_password: str = "DaleAdmin2024#"
    database_name: str = "hyt_bi"
    database_port: int = 3306

    # Output directories
    output_dir: str = "augmented_images"

    # Augmentation settings
    enable_flip: bool = True          # 镜像翻转
    enable_crop: bool = True          # 随机裁剪
    enable_brightness: bool = True    # 亮度调整
    enable_noise: bool = True         # 添加噪点

    # Augmentation parameters
    brightness_range: tuple = (0.7, 1.3)  # 亮度范围
    crop_ratio: float = 0.9               # 裁剪比例 (保留 90% 的图片)
    noise_intensity: float = 0.02         # 噪点强度

    # Number of augmented images per original
    augmentations_per_image: int = 5

    # Batch processing
    batch_size: int = 10
    max_workers: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def DATABASE_URL(self) -> str:
        """Construct MySQL database URL"""
        return f"mysql+aiomysql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"


# Global settings instance
image_settings = ImageAugmentationSettings()
