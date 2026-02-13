import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';

/**
 * 使用CSS媒体查询控制打印内容，只打印编辑器内容
 * @param element HTML元素
 */
export function printEditorContent(element: HTMLElement): void {
  // 获取 ProseMirror 编辑器内容
  const editorContent = element.classList.contains('ProseMirror') 
    ? element 
    : element.querySelector('.ProseMirror') as HTMLElement;
  
  if (!editorContent) {
    console.error('无法找到编辑器内容元素');
    return;
  }
  
  // 保存原始样式
  const originalStyles = {
    maxHeight: editorContent.style.maxHeight,
    overflow: editorContent.style.overflow,
    height: editorContent.style.height,
    border: editorContent.style.border,
    boxShadow: editorContent.style.boxShadow,
    borderRadius: editorContent.style.borderRadius,
    padding: editorContent.style.padding
  };
  
  // 临时修改样式以确保捕获完整内容，并移除外框和滚动条
  editorContent.style.maxHeight = 'none';
  editorContent.style.overflow = 'visible';
  editorContent.style.height = 'auto';
  editorContent.style.border = 'none';
  editorContent.style.boxShadow = 'none';
  editorContent.style.borderRadius = '0';
  editorContent.style.padding = '0';
  
  // 创建一个新的打印样式表
  const style = document.createElement('style');
  style.id = 'print-style';
  style.textContent = `
    @media print {
      body * {
        visibility: hidden;
      }
      
      .ProseMirror, .ProseMirror * {
        visibility: visible;
        border: none !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        overflow: visible !important;
        max-height: none !important;
        height: auto !important;
      }
      
      /* 隐藏标题折叠按钮 */
      .heading-button {
        display: none !important;
      }
      
      .ProseMirror {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        padding: 0;
        box-sizing: border-box;
        background-color: white;
        overflow: visible !important;
        display: block !important;
      }
      
      /* 隐藏所有滚动条 */
      ::-webkit-scrollbar {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
      }
      
      /* 标题样式 */
      h1 { font-size: 24pt; font-weight: bold; margin-bottom: 12pt; }
      h2 { font-size: 18pt; font-weight: bold; margin-bottom: 10pt; }
      h3 { font-size: 14pt; font-weight: bold; margin-bottom: 8pt; }
      
      /* 段落样式 */
      p { font-size: 12pt; line-height: 1.5; margin-bottom: 8pt; }
      
      /* 列表样式 */
      ul, ol { padding-left: 2cm; }
      li { margin-bottom: 4pt; }
      
      /* 表格样式 */
      table { border-collapse: collapse; width: 100%; margin-bottom: 12pt; }
      th, td { border: 1px solid #000; padding: 8pt; text-align: left; }
      th { background-color: #f2f2f2; }
      
      /* 代码块样式 */
      pre { background-color: #f5f5f5; padding: 8pt; border-radius: 4pt; margin-bottom: 12pt; white-space: pre-wrap; }
      code { font-family: monospace; }
      
      /* 引用样式 */
      blockquote { border-left: 4px solid #ddd; padding-left: 12pt; color: #666; margin-left: 0; margin-right: 0; }
      
      /* 数学公式样式 */
      .math-inline, .math-display { font-family: 'KaTeX_Math', serif; }
      
      /* 页面设置 */
      @page {
        size: A4;
        margin: 1cm;
      }
    }
  `;
  
  // 添加到文档
  document.head.appendChild(style);
  
  // 触发打印
  window.print();
  
  // 打印完成后恢复原始样式
  setTimeout(() => {
    const printStyle = document.getElementById('print-style');
    if (printStyle) {
      printStyle.remove();
    }
    
    // 恢复原始样式
    editorContent.style.maxHeight = originalStyles.maxHeight;
    editorContent.style.overflow = originalStyles.overflow;
    editorContent.style.height = originalStyles.height;
    editorContent.style.border = originalStyles.border;
    editorContent.style.boxShadow = originalStyles.boxShadow;
    editorContent.style.borderRadius = originalStyles.borderRadius;
    editorContent.style.padding = originalStyles.padding;
  }, 1000);
}

/**
 * 将HTML内容转换为PDF
 * @param content HTML内容字符串或HTML元素
 * @param filename 文件名
 * @param widthType 宽度类型: 'desktop' 或 'mobile'
 * @returns Promise<Blob> PDF的Blob对象
 */
export async function htmlToPdf(
  content: string | HTMLElement, 
  filename: string = 'document.pdf',
  widthType: 'desktop' | 'mobile' = 'desktop'
): Promise<Blob> {
  try {
    // 创建一个临时容器
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    
    // 根据宽度类型设置容器宽度
    if (widthType === 'mobile') {
      tempContainer.style.width = '450px'; // 移动设备宽度
    } else {
      tempContainer.style.width = '800px'; // 桌面宽度
    }
    
    tempContainer.style.backgroundColor = '#ffffff';
    tempContainer.style.padding = '20px';
    
    // 设置内容
    if (typeof content === 'string') {
      tempContainer.innerHTML = content;
    } else {
      // 如果是HTML元素，克隆它
      const contentClone = content.cloneNode(true) as HTMLElement;
      tempContainer.appendChild(contentClone);
    }
    
    // 添加到文档以便截图
    document.body.appendChild(tempContainer);
    
    // 使用html2canvas捕获整个内容
    const canvas = await html2canvas(tempContainer, {
      scale: 2,  // 提高分辨率
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff',
      windowHeight: tempContainer.scrollHeight,
      height: tempContainer.scrollHeight
    });
    
    // 清理临时元素
    document.body.removeChild(tempContainer);
    
    // 将画布转换为图像数据
    const imgData = canvas.toDataURL('image/jpeg', 1.0);
    
    // 创建一个PDF文档 - 使用毫米作为单位
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    });
    
    // 获取PDF页面尺寸（以毫米为单位）
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    
    // 设置页边距（以毫米为单位）
    const margin = 10;
    const contentWidth = pageWidth - 2 * margin;
    
    // 计算图像尺寸，保持宽高比
    const imgWidth = contentWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    
    console.log('PDF页面尺寸:', pageWidth, 'x', pageHeight, 'mm');
    console.log('图像尺寸:', imgWidth, 'x', imgHeight, 'mm');
    console.log('Canvas尺寸:', canvas.width, 'x', canvas.height, 'px');
    
    // 计算需要的页数
    const pagesCount = Math.ceil(imgHeight / (pageHeight - 2 * margin));
    console.log('需要的页数:', pagesCount);
    
    // 分页处理 - 使用裁剪方法
    let heightLeft = imgHeight;
    let position = 0;
    
    // 添加第一页
    pdf.addImage(imgData, 'JPEG', margin, margin, imgWidth, imgHeight);
    heightLeft -= (pageHeight - 2 * margin);
    
    // 添加后续页面
    while (heightLeft > 0) {
      // 添加新页
      pdf.addPage();
      
      // 计算位置 - 负值表示向上移动图像
      position = position - (pageHeight - 2 * margin);
      
      // 添加图像，但位置向上偏移，显示下一部分内容
      pdf.addImage(imgData, 'JPEG', margin, position + margin, imgWidth, imgHeight);
      
      // 减少剩余高度
      heightLeft -= (pageHeight - 2 * margin);
      
      console.log('添加页面，剩余高度:', heightLeft, 'mm, 位置:', position, 'mm');
    }
    
    // 返回PDF Blob
    return pdf.output('blob');
  } catch (error) {
    console.error('生成PDF时出错:', error);
    throw error;
  }
}

/**
 * 捕获编辑器内容为图片
 * @param element HTML元素
 * @param widthType 宽度类型: 'desktop' 或 'mobile'
 * @returns Promise<string> 图片的Data URL
 */
export async function captureEditorAsImage(element: HTMLElement, widthType: 'desktop' | 'mobile' = 'desktop'): Promise<string> {
  try {
    // 获取 ProseMirror 编辑器内容
    const editorContent = element.classList.contains('ProseMirror') 
      ? element 
      : element.querySelector('.ProseMirror') as HTMLElement;
    
    if (!editorContent) {
      throw new Error('无法找到编辑器内容元素');
    }
    
    // 创建一个临时容器，添加额外的内边距
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    
    // 根据宽度类型设置容器宽度
    if (widthType === 'mobile') {
      tempContainer.style.width = '450px'; // 标准移动设备宽度是375，这里设置450，
    } else {
      tempContainer.style.width = '800px'; // 固定桌面宽度为1024px
    }
    
    tempContainer.style.backgroundColor = '#ffffff';
    tempContainer.style.padding = '20px';
    tempContainer.style.paddingBottom = '40px'; // 底部添加更多空白
    
    // 克隆编辑器内容
    const contentClone = editorContent.cloneNode(true) as HTMLElement;
    
    // 应用样式
    contentClone.style.maxHeight = 'none';
    contentClone.style.overflow = 'visible';
    contentClone.style.height = 'auto';
    contentClone.style.border = 'none';
    contentClone.style.boxShadow = 'none';
    contentClone.style.borderRadius = '0';
    contentClone.style.padding = '0';
    contentClone.style.width = '100%'; // 确保内容适应容器宽度
    
    // 隐藏标题折叠按钮
    const headingButtons = contentClone.querySelectorAll('.heading-button');
    headingButtons.forEach(button => {
      (button as HTMLElement).style.display = 'none';
    });
    
    // 将克隆的内容添加到临时容器
    tempContainer.appendChild(contentClone);
    document.body.appendChild(tempContainer);
    
    // 直接对临时容器进行截图
    const canvas = await html2canvas(tempContainer, {
      scale: 2, // 提高分辨率
      useCORS: true, // 允许加载跨域图片
      logging: false,
      backgroundColor: '#ffffff',
      windowHeight: tempContainer.scrollHeight,
      height: tempContainer.scrollHeight
    });
    
    // 清理临时元素
    document.body.removeChild(tempContainer);
    
    // 返回图像的Data URL
    return canvas.toDataURL('image/png');
  } catch (error) {
    console.error('捕获图像时出错:', error);
    throw error;
  }
}
