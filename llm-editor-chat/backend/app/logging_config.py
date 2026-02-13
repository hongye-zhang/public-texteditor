import logging
import sys

def configure_logging():
    """配置日志系统，设置格式和级别"""
    
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # 默认级别为 INFO
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 将处理器添加到根日志记录器
    root_logger.addHandler(console_handler)
    
    # 为 app.services 模块设置 DEBUG 级别
    services_logger = logging.getLogger("app.services")
    services_logger.setLevel(logging.DEBUG)
    
    # 创建专门用于 DEBUG 级别的控制台处理器
    debug_console_handler = logging.StreamHandler(sys.stdout)
    debug_console_handler.setLevel(logging.DEBUG)
    debug_console_handler.setFormatter(formatter)
    
    # 将 DEBUG 处理器添加到 services 日志记录器
    services_logger.addHandler(debug_console_handler)
