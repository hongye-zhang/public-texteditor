import os
import asyncio
from typing import Any, Dict
from openai import OpenAI

from .base import BaseImageGenerator
from app.config import settings


class OpenAIImageGenerator(BaseImageGenerator):
    """
    使用 OpenAI 最新图像模型 (如 gpt-image-1) 生成图像
    """

    def __init__(self, api_key: str = None, model: str = "dall-e-3"):
        # 初始化 OpenAI 客户端，默认使用 gpt-image-1 模型
        # 直接使用传入的 api_key，否则从全局配置读取
        key = api_key or settings.openai_api_key
        self.client = OpenAI(api_key=key)
        self.model = model

    async def generate_image(self, prompt: str, n: int = 1, size: str = "1024x1024", **kwargs: Any) -> Dict[str, Any]:
        """
        异步生成图像（包装同步调用）
        
        返回标准化的响应格式：
        {
            "data": [
                {"url": "图像URL"}
            ]
        }
        """
        # OpenAI 的 Python SDK 调用是同步的，这里用 asyncio.to_thread 包装
        try:
            # 只保留 OpenAI API 支持的参数
            valid_params = {
                "model": self.model,
                "prompt": prompt,
                "n": n,
                "size": size,
            }
                
            # 调用 API
            response = await asyncio.to_thread(
                lambda: self.client.images.generate(**valid_params)
            )
            
            # 将响应转换为标准格式
            return self._standardize_response(response)
            
        except Exception as e:
            import logging
            logging.error(f"Error generating image: {str(e)}")
            raise
    
    def _standardize_response(self, response) -> Dict[str, Any]:
        """
        将 OpenAI 响应转换为标准格式
        
        处理 b64_json 响应格式，返回格式为：
        {
            "data": [
                {"b64_json": "BASE64编码的图像数据"}
            ]
        }
        """
        try:
            # 检查是否是对象形式的响应
            if hasattr(response, "data") and hasattr(response.data, "__iter__"):
                # 新版 OpenAI API 返回对象
                result = []
                for item in response.data:
                    data_item = {}
                    # 检查是否有 b64_json 属性
                    if hasattr(item, "b64_json") and item.b64_json is not None and item.b64_json != "":
                        data_item["b64_json"] = item.b64_json
                    # 检查是否有 url 属性（兼容旧版）
                    elif hasattr(item, "url"):
                        data_item["url"] = item.url
                    
                    if data_item:  # 只添加非空数据
                        result.append(data_item)
                        
                return {"data": result}
            
            # 检查是否是字典形式的响应
            elif isinstance(response, dict) and "data" in response:
                # 已经是字典格式，直接返回
                return response
            
            # 其他情况，尝试转换为字典
            else:
                if hasattr(response, "__dict__"):
                    resp_dict = response.__dict__
                    if "_data" in resp_dict:
                        data = resp_dict["_data"]
                        result = []
                        for item in data:
                            data_item = {}
                            # 检查 b64_json 和 url 属性
                            if hasattr(item, "b64_json") and item.b64_json is not None and item.b64_json != "":
                                data_item["b64_json"] = item.b64_json
                            elif hasattr(item, "url"):
                                data_item["url"] = item.url
                                
                            if data_item:  # 只添加非空数据
                                result.append(data_item)
                                
                        return {"data": result}
            
            # 如果无法识别格式，抛出异常
            raise ValueError(f"Unrecognized response format: {response}")
            
        except Exception as e:
            import logging
            logging.error(f"Error standardizing response: {str(e)}\nResponse: {response}")
            raise ValueError(f"Failed to process image generation response: {str(e)}")
