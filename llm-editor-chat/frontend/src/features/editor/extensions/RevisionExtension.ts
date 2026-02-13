import { Extension, Node } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { v4 as uuidv4 } from 'uuid';
import { Editor } from '@tiptap/core';
import { Node as ProseMirrorNode, Fragment } from '@tiptap/pm/model';
import type { DOMOutputSpec } from '@tiptap/pm/model';
import { Transaction } from '@tiptap/pm/state';
import type { RawCommands, CommandProps } from '@tiptap/core';

// 修订节点定义
export const RevisionNode = Node.create({
  name: 'revisionNode',
  
  group: 'inline',
  
  content: 'inline*',
  
  inline: true,
  
  defining: true,
  
  addAttributes() {
    return {
      type: {
        default: 'addition', // 'addition', 'deletion', 'substitution'
      },
      status: {
        default: 'pending', // 'pending', 'accepted', 'rejected'
      },
      originalContent: {
        default: '',
      },
      newContent: {
        default: '',
      },
      comment: {
        default: '',
      },
      id: {
        default: () => uuidv4(),
      },
    };
  },
  
  parseHTML() {
    return [
      {
        tag: 'span[data-revision]',
        getAttrs: (node) => {
          if (!(node instanceof HTMLElement)) return {};
          
          // 从HTML元素中提取属性
          return {
            type: node.getAttribute('data-revision-type') || 'addition',
            status: node.getAttribute('data-status') || 'pending',
            id: node.getAttribute('data-revision-id') || uuidv4(),
            originalContent: node.getAttribute('data-original-content') || '',
            newContent: node.getAttribute('data-new-content') || '',
            comment: node.getAttribute('data-comment') || ''
          };
        },
        getContent: (domNode, schema) => { // domNode is the outer span[data-revision]
          if (!(domNode instanceof HTMLElement)) {
            return Fragment.empty;
          }

          const type = domNode.getAttribute('data-revision-type');
          const originalContentValue = domNode.getAttribute('data-original-content');
          const newContentValue = domNode.getAttribute('data-new-content');

          let textForNodeContent = '';
          if (type === 'substitution' || type === 'deletion') {
            textForNodeContent = originalContentValue || '';
          } else if (type === 'addition') {
            textForNodeContent = newContentValue || '';
          }
          // Else, for unknown types or if content is truly empty, textForNodeContent remains ''

          if (!textForNodeContent) {
            return Fragment.empty; // Avoid creating a text node with null/undefined
          }
          // Create a ProseMirror Fragment containing a single text node
          const textNode = schema.text(textForNodeContent);
          return Fragment.from(textNode);
        }
      },
    ];
  },
  
  renderHTML({ HTMLAttributes }): DOMOutputSpec {
    const { type, status, id, originalContent, newContent, comment } = HTMLAttributes;
    
    // 基本容器
    const container: [string, any] = [
      'span',
      {
        'data-revision': '',
        'data-revision-type': type,
        'data-status': status,
        'data-revision-id': id,
        'data-original-content': originalContent || '',
        'data-new-content': newContent || '',
        'data-comment': comment || '',
        'class': `revision revision-${type} revision-${status}`,
      }
    ];
    
    // 基于修订类型渲染不同的内容
    if (type === 'substitution') {
      // 对于替换类型，显示原始内容和新内容，但不显示箭头
      return [
        'span',
        {
          'data-revision': '',
          'data-revision-type': 'substitution',
          'data-status': status,
          'data-revision-id': id,
          'data-original-content': originalContent || '',
          'data-new-content': newContent || '',
          'data-comment': comment || '',
          'class': `revision revision-substitution revision-${status}`,
        },
        ['span', { class: 'revision-original' }, 0],
        ['span', { class: 'revision-new paragraph-revision' }, HTMLAttributes.newContent || ''],
      ] as DOMOutputSpec;
    }
    
    // 添加或删除类型
    container.push(0); // 添加内容占位符
    return container as DOMOutputSpec;
  },
  
  addNodeView() {
    return ({ node, HTMLAttributes, getPos }) => {
      const dom = document.createElement('span');
      dom.setAttribute('data-revision', '');
      dom.setAttribute('data-revision-type', node.attrs.type);
      dom.setAttribute('data-status', node.attrs.status);
      dom.setAttribute('data-revision-id', node.attrs.id);
      dom.setAttribute('data-original-content', node.attrs.originalContent || '');
      dom.setAttribute('data-new-content', node.attrs.newContent || '');
      dom.setAttribute('data-comment', node.attrs.comment || '');
      dom.classList.add('revision', `revision-${node.attrs.type}`, `revision-${node.attrs.status}`);
      
      const contentDOM = document.createElement('span');
      dom.appendChild(contentDOM);
      
      // 对于替换类型，添加额外的元素
      if (node.attrs.type === 'substitution') {
        // 移除内容 DOM，我们将用自定义结构替换它
        dom.removeChild(contentDOM);
        
        // 创建原始内容容器
        const originalSpan = document.createElement('span');
        originalSpan.classList.add('revision-original');
        dom.appendChild(originalSpan);
        
        // 创建新内容容器（作为独立段落）
        const newSpan = document.createElement('span');
        newSpan.classList.add('revision-new', 'paragraph-revision');
        newSpan.textContent = node.attrs.newContent || '';
        dom.appendChild(newSpan);
        
        return {
          dom,
          contentDOM: originalSpan,
        };
      }
      
      return {
        dom,
        contentDOM,
      };
    };
  },
});

// 修订扩展
export const RevisionExtension = Extension.create({
  name: 'revisionCommands',
  
  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },
  
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('revision'),
      }),
    ];
  },
  
  addCommands(): Record<string, any> {
    return {
      addRevision: (options: { type: string; originalContent?: string; newContent?: string; comment?: string }) => 
        ({ tr, chain, dispatch }: { tr: Transaction; chain: any; dispatch: any }) => {
        const { type, originalContent = '', newContent = '', comment = '' } = options;
        
        // 对于替换类型，我们需要同时有原始内容和新内容
        if (type === 'substitution' && (!originalContent || !newContent)) {
          return false;
        }
        
        return chain()
          .insertContent({
            type: 'revisionNode',
            attrs: {
              type,
              status: 'pending',
              originalContent,
              newContent,
              comment,
              id: uuidv4(),
            },
            content: type === 'deletion' || type === 'substitution' 
              ? [{ type: 'text', text: originalContent }]
              : [{ type: 'text', text: newContent }],
          })
          .run();
      },
      
      // 处理选中文本的修订
      createRevisionFromSelection: (options: { type: string; newContent?: string; comment?: string }) => 
        ({ tr, dispatch, chain, state }: { tr: Transaction; dispatch: any; chain: any; state: any }) => {
        const { type, newContent = '', comment = '' } = options;
        const { selection } = state;
        const { from, to } = selection;
        
        // 没有选择文本则不处理
        if (from === to) {
          return false;
        }
        
        const selectedText = state.doc.textBetween(from, to);
        
        return chain()
          .deleteSelection()
          .insertContentAt(from, {
            type: 'revisionNode',
            attrs: {
              type,
              status: 'pending',
              originalContent: selectedText,
              newContent,
              comment,
              id: uuidv4(),
            },
            content: type === 'addition' 
              ? [{ type: 'text', text: newContent }]
              : [{ type: 'text', text: selectedText }],
          })
          .run();
      },
      
      // 接受修订
      acceptRevision: (id: string) => ({ tr, dispatch, state, editor }: { tr: Transaction; dispatch: any; state: any; editor?: any }) => {
        const { doc } = tr;
        let found = false;
        
        // 查找和处理修订节点
        doc.descendants((node: ProseMirrorNode, pos: number) => {
          if (node.type.name === 'revisionNode' && node.attrs.id === id) {
            const { type, newContent } = node.attrs;
            found = true;
            
            if (type === 'deletion') {
              // 接受删除 - 移除节点及其内容
              tr.delete(pos, pos + node.nodeSize);
            } else if (type === 'addition') {
              // 接受添加 - 保留内容但移除修订标记
              const content = node.content;
              tr.replaceWith(pos, pos + node.nodeSize, content);
            } else if (type === 'substitution') {
              // 接受替换 - 用新内容替换原内容
              tr.delete(pos, pos + node.nodeSize);
              tr.insertText(newContent, pos);
            }
            
            found = true;
            return false; // 停止遍历
          }
          return true; // 继续遍历
        });

        if (found && dispatch) {
          dispatch(tr);
          return true;
        }

        return false;
      },
      
      rejectRevision: (id: string) => ({ tr, dispatch, state, editor }: { tr: Transaction; dispatch: any; state: any; editor?: any }) => {
        // 查找修订节点
        const { doc } = tr;
        let found = false;
        
        doc.descendants((node: ProseMirrorNode, pos: number) => {
          if (node.type.name === 'revisionNode' && node.attrs.id === id) {
            const { type } = node.attrs;
            found = true;
            
            if (type === 'deletion') {
              // 拒绝删除 - 保留内容但移除修订标记
              const content = node.content;
              tr.replaceWith(pos, pos + node.nodeSize, content);
            } else if (type === 'addition') {
              // 拒绝添加 - 移除节点及其内容
              tr.delete(pos, pos + node.nodeSize);
            } else if (type === 'substitution') {
              // 拒绝替换 - 保留原始内容
              // 获取原始内容（当前节点的内容）
              const content = node.content;
              tr.replaceWith(pos, pos + node.nodeSize, content);
            }
            
            return false; // 停止遍历
          }
          return true; // 继续遍历
        });

        if (found && dispatch) {
          dispatch(tr);
          
          // 如果有editor实例，触发一个修订状态变化的事件
          if (editor) {
            setTimeout(() => {
              editor.emit('revision:rejected', { id });
            }, 0);
          }
          
          return true;
        }

        return false;
      },
      
      hasPendingRevisions: () => ({ state }: { state: any }) => {
        // 检查文档中是否有待处理的修订
        let hasPending = false;

        state.doc.descendants((node: ProseMirrorNode) => {
          if (node.type.name === 'revisionNode' && node.attrs.status === 'pending') {
            hasPending = true;
            return false; // 找到一个就停止遍历
          }
          return true; // 继续遍历
        });

        return hasPending;
      },
    };
  },
});

// 主扩展 - 组合节点和扩展
export const Revision = Extension.create({
  name: 'revision',
  
  addExtensions() {
    return [
      RevisionNode,
      RevisionExtension,
    ];
  },
});
