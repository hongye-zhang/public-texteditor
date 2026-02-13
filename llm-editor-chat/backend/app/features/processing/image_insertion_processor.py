"""
Image Insertion Processor

This module handles the actual processing of image insertion requests,
converting user prompts into image data and preparing the editor actions.
"""
from typing import Dict, Any, Optional
import logging
import base64

from app.features.processing.image_insertion_service import ImageInsertionService
from app.models.editor_actions import create_action
from app.utils.image_utils import url_to_base64

# 配置日志记录
logger = logging.getLogger(__name__)

class ImageInsertionProcessor:
    """
    Processes image insertion requests and generates appropriate editor actions.
    """
    
    def __init__(self):
        """Initialize the processor with required services."""
        self.image_service = ImageInsertionService()
    
    async def process_image_insertion(
        self, 
        message: str, 
        image_type: str = "aesthetic",
        position: str = "cursor",
        always_base64: bool = True
    ) -> Dict[str, Any]:
        """
        Process an image insertion request and return an editor action.
        
        :param message: User message containing the image prompt
        :param image_type: Type of image to generate ("aesthetic" or "diagram")
        :param position: Position to insert the image ("cursor", "start", or "end")
        :param always_base64: Whether to always convert image URLs to base64
        :return: Editor action dictionary for inserting the image
        """
        try:
            # 生成图像
            image_data = await self.image_service.generate_image(message, image_type)
            
            # 创建插入图像的编辑器动作
            # 根据图像数据类型创建不同的动作
            action_params = {
                "alt_text": image_data["alt_text"],
                "width": image_data["width"],
                "height": image_data["height"],
                "position": position,
                "format": image_data.get("format", "png")
            }
            
            # 如果是 base64 格式的图像数据
            if "is_base64" in image_data and image_data["is_base64"]:
                action_params["data"] = image_data["image_data"]
                action_params["is_base64"] = True
                logger.info("Using base64 image data directly")
            # 如果是 URL 格式，但需要转换为base64
            elif "image_url" in image_data and always_base64:
                logger.info(f"Converting image URL to base64: {image_data['image_url'][:50]}...")
                try:
                    # 将URL转换为base64
                    base64_data, mime_type = await url_to_base64(image_data["image_url"])
                    if base64_data:
                        # 成功转换为base64
                        action_params["data"] = base64_data
                        action_params["is_base64"] = True
                        action_params["mime_type"] = mime_type
                        logger.info("Successfully converted image URL to base64")
                    else:
                        # 转换失败，回退到URL
                        logger.warning("Failed to convert image URL to base64, falling back to URL")
                        action_params["url"] = image_data["image_url"]
                except Exception as e:
                    # 出现异常，回退到URL
                    logger.error(f"Error converting image URL to base64: {str(e)}")
                    action_params["url"] = image_data["image_url"]
            # 如果是URL格式，且不需要转换
            elif "image_url" in image_data:
                action_params["url"] = image_data["image_url"]
                logger.info("Using image URL directly")
            else:
                raise ValueError("Image data does not contain URL or base64 data")
                
            # 创建动作
            action = create_action("insert-image", **action_params)
            
            return action
        except Exception as e:
            logger.error(f"Error processing image insertion: {str(e)}")
            # 返回错误信息
            return {
                "type": "error",
                "message": f"Failed to process image insertion: {str(e)}"
            }
