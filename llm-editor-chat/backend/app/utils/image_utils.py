"""
图像处理工具函数

提供图像处理相关的工具函数，如URL转base64等
"""

import base64
import logging
from typing import Optional, Tuple
import aiohttp
from io import BytesIO

logger = logging.getLogger(__name__)

async def url_to_base64(image_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    将图片URL转换为base64编码
    
    :param image_url: 图片URL
    :return: (base64编码的图片数据, MIME类型)，如果失败则返回(None, None)
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch image from {image_url}, status: {response.status}")
                    return None, None
                
                # 获取图片内容和MIME类型
                image_data = await response.read()
                content_type = response.headers.get('Content-Type', 'image/png')
                
                # 转换为base64
                base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # 返回带有MIME类型的base64数据
                return base64_data, content_type
    except Exception as e:
        logger.error(f"Error converting image URL to base64: {str(e)}")
        return None, None
