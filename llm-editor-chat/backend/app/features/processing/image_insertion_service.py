"""
Image Insertion Processing Service

This module encapsulates functionality for handling image insertion in documents.
"""

from typing import Dict, Any, Optional, List
import os
import json
import asyncio
import logging
from app.config import settings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from .images.openai_generator import OpenAIImageGenerator

# 配置日志记录
logger = logging.getLogger(__name__)

# 使用全局配置
api_key = settings.openai_api_key
image_model = settings.openai_image_model

class ImageInsertionService:
    """Service to process and insert images into documents."""
    
    def __init__(self):
        """Initialize the image insertion service."""
        # 无需在此保存模型，直接在调用时传参
        pass
    
    async def generate_image(self, message: str, image_type: str = "aesthetic", **kwargs) -> dict:
        """
        根据用户消息生成图像的通用方法
        
        :param message: 用户输入的提示词
        :param image_type: 图像类型，如"aesthetic"或"diagram"
        :return: 包含图像数据或URL的字典，可用于创建编辑器动作
        """
        if image_type == "aesthetic":
            return await self.generate_aesthetic_image(message, **kwargs)
        elif image_type == "diagram":
            return await self.generate_diagram_image(message, **kwargs)
        else:
            raise ValueError(f"Unsupported image type: {image_type}")
    
    async def generate_aesthetic_image(self, message: str, **kwargs) -> dict:
        """
        生成美学/艺术类图像
        
        :param message: 用户输入的提示词
        :return: 包含图像数据或URL的字典
        """
        # 步骤1: 优化用户的原始提示词为更结构化的提示词
        optimized_prompt = await self._optimize_aesthetic_prompt(message)
        
        # 记录优化后的提示词，便于调试
        logger.info(f"优化后的图像提示词: {optimized_prompt[:100]}...")
        
        # 步骤2: 调用 OpenAI 图像生成
        generator = OpenAIImageGenerator(api_key=api_key, model=image_model)
        size = kwargs.get("size", "1024x1024")
        n = kwargs.get("n", 1)
        # 调用图像生成API
        resp = await generator.generate_image(optimized_prompt, n=n, size=size)
        
        # 从响应中提取 base64 数据
        if "data" in resp and len(resp["data"]) > 0:
            image_data = resp["data"][0]
            # 提取宽度和高度
            width, height = map(int, size.split("x"))
            
            # 检查是否有 base64 数据
            if "b64_json" in image_data and image_data["b64_json"] is not None and len(image_data["b64_json"]) > 0:
                # 返回包含 base64 数据的字典
                return {
                    "image_data": image_data["b64_json"],
                    "alt_text": f"Generated image based on: {message}",
                    "width": width,
                    "height": height,
                    "format": "png",
                    "is_base64": True
                }
            # 兼容 URL 格式
            elif "url" in image_data:
                return {
                    "image_url": image_data["url"],
                    "alt_text": f"Generated image based on: {message}",
                    "width": width,
                    "height": height,
                    "format": "png"
                }
        
        # 如果无法提取数据，抛出异常
        raise ValueError(f"Failed to extract image data from response: {resp}")
    
    async def generate_diagram_image(self, message: str, **kwargs) -> dict:
        """
        生成概念图/图表类图像
        
        :param message: 用户输入的提示词
        :return: 包含图像数据或URL的字典
        """
        # 步骤1: 优化用户的原始提示词为更结构化的提示词
        optimized_prompt = await self._optimize_diagram_prompt(message)
        
        # 记录优化后的提示词，便于调试
        print(f"优化后的图表提示词: {optimized_prompt}")
        
        # 步骤2: 调用 OpenAI 图像生成
        generator = OpenAIImageGenerator(api_key=api_key, model=image_model)
        size = kwargs.get("size", "1024x1024")
        n = kwargs.get("n", 1)
        # 调用图像生成API
        resp = await generator.generate_image(optimized_prompt, n=n, size=size)
        
        # 从响应中提取 base64 数据
        if "data" in resp and len(resp["data"]) > 0:
            image_data = resp["data"][0]
            # 提取宽度和高度
            width, height = map(int, size.split("x"))
            
            # 检查是否有 base64 数据
            if "b64_json" in image_data and image_data["b64_json"] is not None and len(image_data["b64_json"]) > 0:
                # 返回包含 base64 数据的字典
                return {
                    "image_data": image_data["b64_json"],
                    "alt_text": f"Generated diagram based on: {message}",
                    "width": width,
                    "height": height,
                    "format": "png",
                    "is_base64": True
                }
            # 兼容 URL 格式
            elif "url" in image_data:
                return {
                    "image_url": image_data["url"],
                    "alt_text": f"Generated diagram based on: {message}",
                    "width": width,
                    "height": height,
                    "format": "png"
                }
        
        # 如果无法提取数据，抛出异常
        raise ValueError(f"Failed to extract image data from response: {resp}")
    
    async def _optimize_diagram_prompt(self, user_prompt: str) -> str:
        """
        将用户的原始提示词优化为更结构化的图表生成提示词
        
        :param user_prompt: 用户的原始提示词
        :return: 优化后的提示词
        """
        # 这里可以调用LLM来优化提示词
        # 在实际实现中，应该使用项目中已有的LLM服务
        
        # 优化提示词模板
        optimization_prompt = f"""You are a professional vector diagram generation expert. Please transform the following user's original prompt:  
"{user_prompt}"  
into a structured, detailed, and concise vector diagram drawing prompt, requiring the following elements:

1. **Subject**  
   - Briefly summarize the core concept or process to be conveyed in the diagram.

2. **Style**  
   - Clearly specify style keywords such as "vector infographic," "flat design," "technical illustration," etc.

3. **Composition**  
   - The number, arrangement, and connection relationships of layers, arrows, and labels.  
   - Whether semi-transparent, solid, grid-aligned, or other effects are needed.

4. **Color Palette**  
   - Recommend which primary colors to use, and whether to adopt high-contrast, flat, or corporate colors.

5. **Format & Quality**  
   - Resolution (e.g., 4K), file format (e.g., SVG), canvas aspect ratio (e.g., 16:9), etc.

Please integrate the above elements into a single complete prompt so that it can be directly used to call the AI to generate a high-quality vector diagram."""
        
        # 使用OpenAI API调用o4-mini模型优化提示词
        try:
            # 创建ChatOpenAI实例
            chat_model = ChatOpenAI(
                api_key=api_key,  # 使用全局API密钥
                model=self.default_model,
                temperature=0.7,
                verbose=True
            )
            
            # 准备消息
            messages = [
                SystemMessage(content="You are a professional vector diagram generation expert."),
                HumanMessage(content=optimization_prompt)
            ]
            
            # 调用API
            logger.info(f"Calling OpenAI API to optimize diagram prompt for: {user_prompt[:50]}...")
            response = chat_model.invoke(messages)
            
            # 提取响应内容
            optimized_prompt = response.content
            logger.info(f"Successfully optimized diagram prompt")
            
        except Exception as e:
            # 如果调用失败，记录错误并使用默认提示词
            logger.error(f"Error calling OpenAI API: {str(e)}", exc_info=True)
            # 默认提示词作为备用
            optimized_prompt = f"Create a professional vector diagram illustrating {user_prompt}. Use flat design style with a corporate color palette (blue, gray, and accent orange). Arrange elements in a logical flow with connecting arrows and clear labels. Include semi-transparent overlays for emphasis. Output as high-resolution SVG with 16:9 aspect ratio."
        
        return optimized_prompt
    
    async def _optimize_aesthetic_prompt(self, user_prompt: str) -> str:
        """
        将用户的原始提示词优化为更结构化的图像生成提示词
        
        :param user_prompt: 用户的原始提示词
        :return: 优化后的提示词
        """
        # 优化提示词模板
        optimization_prompt = f"""You are an expert image-generation orchestrator. Given a user's original prompt "{user_prompt}", first detect their intent:

1. **Vector Diagram**: schematic, flowchart, infographic, or other diagrammatic illustration.  
2. **Photography**: realistic photo taken with a camera or mobile device.  
3. **Photorealistic CG**: full 3D render or CGI that mimics reality.  
4. **Illustration / Digital Painting**: artistic drawing, painting, or sketch.

Then, based on the detected intent, transform "{user_prompt}" into a single, structured, detailed, and concise prompt optimized for that category:

---

**If Vector Diagram:**  
• **Subject**: brief core concept or process.  
• **Style**: "vector infographic," "flat design," "technical illustration."  
• **Composition**: layers, arrows, labels, alignment, transparency.  
• **Color Palette**: primary colors, contrast level.  
• **Format & Quality**: resolution (e.g. 4K), format (SVG), aspect ratio (16:9).

**If Photography:**  
- **DSLR/Mirrorless Photo:**  
  1. **Camera & Lens**: e.g. "Canon EOS R5, 85 mm f/1.2."  
  2. **Lighting**: e.g. "golden-hour backlight with softbox fill."  
  3. **Composition**: rule of thirds, shallow depth of field, bokeh.  
  4. **Post-Processing**: film simulation (e.g. "Kodak Portra 400"), subtle color grading.  

- **Mobile / Social-Style Photo:**  
  1. **Phone Model & Specs**: e.g. "iPhone 15 Pro, 1.9 μm pixel sensor, ƒ/1.6."  
  2. **Depth & Bokeh**: "Portrait Mode shallow depth of field, smooth bokeh."  
  3. **Filter & Texture**: "Snapchat-style warm filter, slight film grain, soft vignette."  
  4. **Lighting & Framing**: "natural window light, candid framing, rule of thirds."  
  5. **Post-Processing**: enhanced saturation, subtle skin smoothing, light flares.

**If Photorealistic CG:**  
1. **Render Engine & Settings**: e.g. "Octane, unbiased path-tracing, 1024 samples."  
2. **Materials & Textures**: PBR materials, 8K textures, subsurface scattering.  
3. **Lighting**: HDRI environment, three-point soft light.  
4. **Camera**: "35 mm f/2.8, 1/100 s, ISO 100."  
5. **Post-Processing**: realistic color grading, lens flares, film grain.

**If Illustration / Digital Painting:**  
1. **Style & Medium**: e.g. "digital oil painting," "watercolor sketch."  
2. **Brushwork & Texture**: "visible brush strokes," "canvas texture overlay."  
3. **Color & Mood**: "warm pastel palette," "dramatic chiaroscuro."  
4. **Composition & Focus**: dynamic perspective, dramatic lighting, hand-painted details.

---

**Final Output:**  
Return exactly one prompt string, fully assembled according to the detected category, ready for direct submission to the AI image-generation engine."""
        
        try:
            # 创建ChatOpenAI实例
            chat_model = ChatOpenAI(
                api_key=api_key,  # 使用全局API密钥
                model=image_model,
                temperature=0.7,
                verbose=True
            )
            
            # 准备消息
            messages = [
                SystemMessage(content="You are an expert image-generation orchestrator."),
                HumanMessage(content=optimization_prompt)
            ]
            
            # 调用API
            logger.info(f"Calling OpenAI API to optimize aesthetic image prompt for: {user_prompt[:50]}...")
            response = chat_model.invoke(messages)
            
            # 提取响应内容
            optimized_prompt = response.content
            logger.info(f"Successfully optimized aesthetic image prompt")
            
        except Exception as e:
            # 如果调用失败，记录错误并使用默认提示词
            logger.error(f"Error calling OpenAI API: {str(e)}", exc_info=True)
            # 默认提示词作为备用
            optimized_prompt = f"Create a professional, high-quality image of {user_prompt}. Use realistic lighting, detailed textures, and vibrant colors. Ensure the composition is balanced and visually appealing."
        
        return optimized_prompt
