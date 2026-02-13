from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseImageGenerator(ABC):
    """
    抽象基类，定义图像生成器接口
    """

    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """
        根据给定提示词异步生成图像

        :param prompt: 文本提示词
        :return: 包含生成结果的字典
        """
        pass
