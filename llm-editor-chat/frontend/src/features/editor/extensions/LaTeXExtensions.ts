import { Node, mergeAttributes } from '@tiptap/core';
import katex from 'katex';

// 辅助函数：HTML转义
export function escapeHTML(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// 辅助函数：HTML反转义
export function unescapeHTML(html: string): string {
  return html
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#039;/g, "'");
}

// 辅助函数：检查字符串是否为有效的LaTeX公式
export function isValidLatex(formula: string): boolean {
  if (!formula || formula.trim() === '') return false;
  try {
    // 尝试渲染公式到一个临时元素
    const tempElement = document.createElement('div');
    katex.render(formula, tempElement, { throwOnError: false });
    return true;
  } catch (error) {
    console.warn('LaTeX validation error:', error);
    return false;
  }
}

// 自定义LaTeX节点：行内数学
export const InlineMath = Node.create({
  name: 'inlineMath',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,
  draggable: true,
  
  addAttributes() {
    return {
      formula: {
        default: '',
        parseHTML: element => {
          const formula = element.getAttribute('data-formula');
          return formula || '';
        },
        renderHTML: attributes => {
          return {
            'data-formula': attributes.formula,
          };
        },
      },
    };
  },
  
  parseHTML() {
    return [
      {
        tag: 'span[data-type="inline-math"]',
        getAttrs: (node) => {
          if (typeof node === 'string') return {};
          const element = node as HTMLElement;
          const formula = element.getAttribute('data-formula') || '';
          return { formula };
        },
      },
      // 支持从HTML中解析KaTeX渲染的内容
      {
        tag: 'span.katex',
        getAttrs: (node) => {
          if (typeof node === 'string') return false;
          const element = node as HTMLElement;
          const mathElement = element.querySelector('.katex-mathml annotation');
          if (!mathElement) return false;
          const formula = mathElement.textContent || '';
          return { formula };
        },
      },
    ];
  },
  
  renderHTML({ HTMLAttributes }) {
    // 确保在序列化时保留公式内容
    const formula = HTMLAttributes.formula || '';
    return ['span', mergeAttributes(HTMLAttributes, { 
      'data-type': 'inline-math',
      'data-formula': formula,
      'class': 'latex-node inline-math',
    })];
  },
  
  addNodeView() {
    return ({ node, HTMLAttributes, getPos, editor }) => {
      const dom = document.createElement('span');
      dom.setAttribute('data-type', 'inline-math');
      dom.setAttribute('data-formula', node.attrs.formula || '');
      
      const formula = unescapeHTML(node.attrs.formula || '');
      // 渲染LaTeX公式
      try {
        katex.render(formula, dom, { throwOnError: false });
      } catch (error) {
        dom.textContent = formula;
        console.error('KaTeX rendering error:', error);
      }
      
      // 添加点击事件处理
      dom.addEventListener('click', () => {
        const newFormula = prompt('Edit formula:', formula);
        if (newFormula !== null && typeof getPos === 'function') {
          const pos = getPos();

          const transaction = editor.state.tr.setNodeMarkup(pos, undefined, {
            ...node.attrs,
            formula: newFormula,
          });
          editor.view.dispatch(transaction);
        }
      });
      
      return {
        dom,
        update: (updatedNode) => {
          if (updatedNode.attrs.formula !== formula) {
            const newFormula = unescapeHTML(updatedNode.attrs.formula || '');
            dom.setAttribute('data-formula', updatedNode.attrs.formula || '');
            
            try {
              katex.render(newFormula, dom, { throwOnError: false });
            } catch (error) {
              dom.textContent = updatedNode.attrs.formula;
              console.error('KaTeX rendering error:', error);
            }
            return true;
          }
          return false;
        },
        ignoreMutation: () => true, // 忽略DOM变化，防止Tiptap尝试修改KaTeX渲染的内容
        stopEvent: (event) => {
          // 阻止编辑器处理点击事件，让我们自己的点击处理程序处理
          return event.type === 'click';
        },
      };
    };
  },
});

// 自定义LaTeX节点：块级数学
export const BlockMath = Node.create({
  name: 'blockMath',
  group: 'block',
  content: '',
  selectable: true,
  draggable: true,
  
  addAttributes() {
    return {
      formula: {
        default: '',
        parseHTML: element => {
          const formula = element.getAttribute('data-formula');
          return formula || '';
        },
        renderHTML: attributes => {
          return {
            'data-formula': attributes.formula,
          };
        },
      },
    };
  },
  
  parseHTML() {
    return [
      {
        tag: 'div[data-type="block-math"]',
        getAttrs: (node) => {
          if (typeof node === 'string') return {};
          const element = node as HTMLElement;
          const formula = element.getAttribute('data-formula') || '';
          return { formula };
        },
      },
      // 支持从HTML中解析KaTeX渲染的块级内容
      {
        tag: 'div.katex-display',
        getAttrs: (node) => {
          if (typeof node === 'string') return false;
          const element = node as HTMLElement;
          const katexElement = element.querySelector('.katex');
          if (!katexElement) return false;
          const mathElement = katexElement.querySelector('.katex-mathml annotation');
          if (!mathElement) return false;
          const formula = mathElement.textContent || '';
          return { formula };
        },
      },
    ];
  },
  
  renderHTML({ HTMLAttributes }) {
    // 确保在序列化时保留公式内容
    const formula = HTMLAttributes.formula || '';
    return ['div', mergeAttributes(HTMLAttributes, { 
      'data-type': 'block-math',
      'data-formula': formula,
      'class': 'latex-node block-math',
    })];
  },
  
  addNodeView() {
    return ({ node, HTMLAttributes, getPos, editor }) => {
      const dom = document.createElement('div');
      dom.setAttribute('data-type', 'block-math');
      dom.setAttribute('data-formula', node.attrs.formula || '');
      dom.style.textAlign = 'center';
      dom.style.margin = '1rem 0';
      
      const formula = unescapeHTML(node.attrs.formula || '');
      // 渲染LaTeX公式
      try {
        katex.render(formula, dom, { 
          throwOnError: false,
          displayMode: true 
        });
      } catch (error) {
        dom.textContent = formula;
        console.error('KaTeX rendering error:', error);
      }
      
      // 添加点击事件处理
      dom.addEventListener('click', () => {
        const newFormula = prompt('Edit formula:', formula);
        if (newFormula !== null && typeof getPos === 'function') {
          const pos = getPos();

          const transaction = editor.state.tr.setNodeMarkup(pos, undefined, {
            ...node.attrs,
            formula: newFormula,
          });
          editor.view.dispatch(transaction);
        }
      });
      
      return {
        dom,
        update: (updatedNode) => {
          if (updatedNode.attrs.formula !== formula) {
            const newFormula = unescapeHTML(updatedNode.attrs.formula || '');
            dom.setAttribute('data-formula', updatedNode.attrs.formula || '');
            
            try {
              katex.render(newFormula, dom, { 
                throwOnError: false,
                displayMode: true 
              });
            } catch (error) {
              dom.textContent = updatedNode.attrs.formula;
              console.error('KaTeX rendering error:', error);
            }
            return true;
          }
          return false;
        },
        ignoreMutation: () => true, // 忽略DOM变化，防止Tiptap尝试修改KaTeX渲染的内容
        stopEvent: (event) => {
          // 阻止编辑器处理点击事件，让我们自己的点击处理程序处理
          return event.type === 'click';
        },
      };
    };
  },
});
