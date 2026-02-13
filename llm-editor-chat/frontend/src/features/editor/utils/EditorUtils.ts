import { Editor } from '@tiptap/core';
import { escapeHTML } from '../extensions/LaTeXExtensions';

// 修复LaTeX标签的HTML转义问题
export function fixLatexHtmlEscaping(html: string): string {
  if (!html) return html;
  
  // 修复被转义的LaTeX标签
  let fixed = html.replace(/&lt;span data-type="inline-math" data-formula="([^"]+)"&gt;/g, 
    '<span data-type="inline-math" data-formula="$1">');
  fixed = fixed.replace(/&lt;div data-type="block-math" data-formula="([^"]+)"&gt;/g, 
    '<div data-type="block-math" data-formula="$1">');
  fixed = fixed.replace(/&lt;\/span&gt;/g, '</span>');
  fixed = fixed.replace(/&lt;\/div&gt;/g, '</div>');
  
  return fixed;
}

// 处理粘贴内容中的LaTeX
export function processLatexInPastedContent(editor: Editor, event: ClipboardEvent): void {
  if (!editor) return;
  
  const text = event.clipboardData?.getData('text/plain');
  if (!text) return;

  console.log('Processing LaTeX in pasted content:', text);

  // 初始化变量
  let processedText = text;
  let hasLatex = false;
  
  // 预处理文本，处理转义的美元符号
  processedText = processedText.replace(/\\\$/g, '$'); // 将\$转义符替换为普通的$符号
  
  // 处理各种 LaTeX 格式
  const inlineLatexRegex = /\$((?!\$).*?)\$/g;            // $...$ 格式
  const blockLatexRegex = /\$\$(.*?)\$\$/g;               // $$...$$ 格式
  const inlineParenLatexRegex = /\\\((.*?)\\\)/g;         // \(...\) 格式
  const blockBracketLatexRegex = /\\\[(.*?)\\\]/g;         // \[...\] 格式
  const equationEnvRegex = /\\begin\{equation\}(.*?)\\end\{equation\}/gs;  // \begin{equation}...\end{equation} 格式
  
  console.log('After preprocessing:', processedText);
  
  // 处理块级LaTeX ($$...$$)
  processedText = processedText.replace(blockLatexRegex, (match, formula) => {
    hasLatex = true;
    console.log('Found block LaTeX:', formula);
    return `<div data-type="block-math" data-formula="${escapeHTML(formula.trim())}"></div>`;
  });

  // 处理行内LaTeX ($...$)
  processedText = processedText.replace(inlineLatexRegex, (match, formula) => {
    hasLatex = true;
    console.log('Found inline LaTeX:', formula);
    return `<span data-type="inline-math" data-formula="${escapeHTML(formula.trim())}"></span>`;
  });
  
  // 处理行内LaTeX (\(...\))
  processedText = processedText.replace(inlineParenLatexRegex, (match, formula) => {
    hasLatex = true;
    console.log('Found inline paren LaTeX:', formula);
    return `<span data-type="inline-math" data-formula="${escapeHTML(formula.trim())}"></span>`;
  });
  
  // 处理块级LaTeX (\[...\])
  processedText = processedText.replace(blockBracketLatexRegex, (match, formula) => {
    hasLatex = true;
    console.log('Found block bracket LaTeX:', formula);
    return `<div data-type="block-math" data-formula="${escapeHTML(formula.trim())}"></div>`;
  });
  
  // 处理方程环境 (\begin{equation}...\end{equation})
  processedText = processedText.replace(equationEnvRegex, (match, formula) => {
    hasLatex = true;
    console.log('Found equation environment:', formula);
    return `<div data-type="block-math" data-formula="${escapeHTML(formula.trim())}"></div>`;
  });

  // 处理方括号格式的LaTeX
  if (processedText.includes('[') && processedText.includes(']')) {
    const lines = processedText.split('\n');
    let inLatexBlock = false;
    let latexContent = '';
    let result = '';

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line === '[' || line.startsWith('\\[')) {
        inLatexBlock = true;
        latexContent = '';
        continue;
      }
      if (inLatexBlock && (line === ']' || line.includes('\\]'))) {
        inLatexBlock = false;
        hasLatex = true;
        result += `<div data-type="block-math" data-formula="${escapeHTML(latexContent.trim())}"></div>`;
        continue;
      }
      if (inLatexBlock) {
        latexContent += (latexContent ? '\n' : '') + line;
      } else {
        result += line + '\n';
      }
    }
    if (result.trim()) {
      processedText = result;
    }
  }

  // 如果包含 LaTeX，插入处理后的内容
  if (hasLatex) {
    console.log('Inserting processed LaTeX content:', processedText);
    // 注意：事件阻止已经在调用方处理
    editor.commands.insertContent(processedText);
  } else {
    console.log('No LaTeX content found in pasted text');
  }
}

// 获取编辑器内容（HTML格式）
export function getEditorHTML(editor: Editor): string {
  if (!editor) return '';
  
  try {
    return editor.getHTML();
  } catch (error) {
    console.error('获取HTML内容时出错:', error);
    return '';
  }
}

// 获取编辑器内容（纯文本格式）
export function getEditorText(editor: Editor): string {
  if (!editor) return '';
  
  try {
    return editor.getText();
  } catch (error) {
    console.error('获取纯文本内容时出错:', error);
    return '';
  }
}

// 获取编辑器内容（原始HTML或转换后的Markdown）
export function getEditorContent(editor: Editor): string {
  if (!editor) return '';
  
  try {
    // 首先尝试获取HTML
    const html = editor.getHTML();
    if (html && html.trim() !== '') {
      return html;
    }
    
    // 如果HTML为空，尝试获取纯文本
    const text = editor.getText();
    if (text && text.trim() !== '') {
      return text;
    }
    
    return '<!-- 编辑器内容为空 -->';
  } catch (error) {
    console.error('获取编辑器内容时出错:', error);
    return '<!-- 获取编辑器内容时出错 -->';
  }
}

// 获取原始Markdown内容（或HTML作为备用）
export function getRawMarkdown(editor: Editor): string {
  if (!editor) {
    console.error('编辑器未初始化');
    return '<!-- 编辑器未初始化 -->';
  }
  
  try {
    // 检查Markdown扩展是否存在
    if (editor.extensionManager.extensions.find(ext => ext.name === 'markdown')) {
      console.log('找到Markdown扩展');
      
      try {
        // 获取HTML内容
        const html = editor.getHTML();
        console.log('获取到HTML内容:', html);
        
        // 返回HTML内容作为备用
        return `<!-- 以下是编辑器内容的HTML表示 -->\n\n${html}`;
      } catch (htmlError) {
        console.error('获取HTML时出错:', htmlError);
        return '<!-- 无法获取HTML内容 -->';
      }
    } else {
      console.warn('未找到Markdown扩展');
      
      // 尝试获取HTML内容
      try {
        const html = editor.getHTML();
        return `<!-- 未找到Markdown扩展，以下是HTML内容 -->\n\n${html}`;
      } catch (htmlError) {
        console.error('获取HTML时出错:', htmlError);
        return '<!-- 无法获取编辑器内容 -->';
      }
    }
  } catch (error) {
    console.error('获取Markdown源码时出错:', error);
    
    // 尝试获取HTML
    try {
      const html = editor.getHTML();
      return `<!-- 获取Markdown源码时出错，以下是HTML内容 -->\n\n${html}`;
    } catch (htmlError) {
      console.error('获取HTML时出错:', htmlError);
      return '<!-- 无法获取编辑器内容 -->';
    }
  }
}
