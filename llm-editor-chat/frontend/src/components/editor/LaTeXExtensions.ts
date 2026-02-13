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

// 自定义LaTeX节点：行内数学
export const InlineMath = Node.create({
  name: 'inlineMath',
  group: 'inline',
  inline: true,
  atom: true,
  
  addAttributes() {
    return {
      formula: {
        default: '',
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
          return {
            formula: element.getAttribute('data-formula') || '',
          };
        },
      },
    ];
  },
  
  renderHTML({ HTMLAttributes }) {
    return ['span', mergeAttributes(HTMLAttributes, { 
      'data-type': 'inline-math',
      'data-formula': HTMLAttributes.formula,
    }), 0];
  },
  
  addNodeView() {
    return ({ node, HTMLAttributes, getPos, editor }) => {
      const dom = document.createElement('span');
      dom.setAttribute('data-type', 'inline-math');
      
      const formula = unescapeHTML(node.attrs.formula || '');
      try {
        katex.render(formula, dom, { throwOnError: false });
      } catch (error) {
        dom.textContent = formula;
        console.error('KaTeX error:', error);
      }
      
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
            try {
              katex.render(unescapeHTML(updatedNode.attrs.formula || ''), dom, { throwOnError: false });
            } catch (error) {
              dom.textContent = updatedNode.attrs.formula;
              console.error('KaTeX error:', error);
            }
            return true;
          }
          return false;
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
  
  addAttributes() {
    return {
      formula: {
        default: '',
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
          return {
            formula: element.getAttribute('data-formula') || '',
          };
        },
      },
    ];
  },
  
  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 
      'data-type': 'block-math',
      'data-formula': HTMLAttributes.formula,
    }), 0];
  },
  
  addNodeView() {
    return ({ node, HTMLAttributes, getPos, editor }) => {
      const dom = document.createElement('div');
      dom.setAttribute('data-type', 'block-math');
      dom.style.textAlign = 'center';
      dom.style.margin = '1rem 0';
      
      const formula = unescapeHTML(node.attrs.formula || '');
      try {
        katex.render(formula, dom, { 
          throwOnError: false,
          displayMode: true 
        });
      } catch (error) {
        dom.textContent = formula;
        console.error('KaTeX error:', error);
      }
      
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
            try {
              katex.render(unescapeHTML(updatedNode.attrs.formula || ''), dom, { 
                throwOnError: false,
                displayMode: true 
              });
            } catch (error) {
              dom.textContent = updatedNode.attrs.formula;
              console.error('KaTeX error:', error);
            }
            return true;
          }
          return false;
        },
      };
    };
  },
});
