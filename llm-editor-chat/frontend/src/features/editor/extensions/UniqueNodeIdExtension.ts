import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';

// 定义插件的状态接口
interface UniqueNodeIdPluginState {
  initialized: boolean;
}

/**
 * UniqueNodeId 扩展
 * 为文档中的每个节点添加唯一 ID
 */
export const UniqueNodeId = Extension.create({
  name: 'uniqueNodeId',

  addOptions() {
    return {
      // 需要添加 ID 的节点类型列表，默认为所有块级节点
      types: [
        'paragraph',
        'heading',
        'blockquote',
        'bulletList',
        'orderedList',
        'listItem',
        'codeBlock',
        'image',
        'table',
      ],
      // ID 属性名称
      attributeName: 'id',
      // 是否在初始化时为所有节点添加 ID
      addIdOnInit: true,
      // ID 生成函数 - 生成 4 位的数字或小写字母 ID
      generateId: () => {
        // 可能的字符：0-9, a-z
        const chars = '0123456789abcdefghijklmnopqrstuvwxyz';
        let id = 'n';
        
        // 生成 4 位 ID，每一位可以是数字或小写字母
        for (let i = 0; i < 4; i++) {
          const randomIndex = Math.floor(Math.random() * chars.length);
          id += chars[randomIndex];
        }
        
        return id;
      },
    };
  },

  // 为指定的节点类型添加 ID 属性
  addGlobalAttributes() {
    return this.options.types.map((type: string) => ({
      types: [type],
      attributes: {
        [this.options.attributeName]: {
          default: null,
          parseHTML: (element: HTMLElement) => element.getAttribute(`data-${this.options.attributeName}`) || null,
          renderHTML: (attributes: Record<string, any>) => {
            if (!attributes[this.options.attributeName]) {
              return {};
            }

            return {
              [`data-${this.options.attributeName}`]: attributes[this.options.attributeName],
            };
          },
        },
      },
    }));
  },

  // 添加 ProseMirror 插件
  addProseMirrorPlugins() {
    const { types, attributeName, addIdOnInit, generateId } = this.options;
    const pluginKey = new PluginKey('uniqueNodeId');

    return [
      new Plugin({
        key: pluginKey,
        state: {
          init: () => ({ initialized: false }),
          apply: (tr, state: UniqueNodeIdPluginState) => {
            // 如果已经初始化过，不再重复初始化
            if (tr.getMeta('uniqueNodeIdInit')) {
              return { initialized: true };
            }
            return state;
          },
        },
        appendTransaction: (transactions, oldState, newState) => {
          // 跳过只读事务
          if (newState.doc === oldState.doc) {
            return null;
          }

          const pluginState = pluginKey.getState(newState);
          const tr = newState.tr;
          let modified = false;

          // 初始化：为所有现有节点添加 ID
          if (addIdOnInit && !pluginState.initialized) {
            newState.doc.descendants((node, pos) => {
              if (types.includes(node.type.name) && node.attrs[attributeName] === null) {
                tr.setNodeMarkup(pos, null, {
                  ...node.attrs,
                  [attributeName]: generateId(),
                });
                modified = true;
              }
            });

            if (modified) {
              tr.setMeta('uniqueNodeIdInit', true);
            }
          } else {
            // 为新添加的节点添加 ID
            const addedNodes = findAddedNodes(oldState.doc, newState.doc, types);
            
            addedNodes.forEach(({ node, pos }) => {
              if (node.attrs[attributeName] === null) {
                tr.setNodeMarkup(pos, null, {
                  ...node.attrs,
                  [attributeName]: generateId(),
                });
                modified = true;
              }
            });
          }

          return modified ? tr : null;
        },
      }),
    ];
  },
});

/**
 * 查找新添加的节点
 * 这是一个简化的实现，只检查新文档中没有 ID 的节点
 */
function findAddedNodes(oldDoc: any, newDoc: any, types: string[]) {
  const result: { node: any; pos: number }[] = [];

  newDoc.descendants((node: any, pos: number) => {
    if (types.includes(node.type.name) && node.attrs.id === null) {
      result.push({ node, pos });
    }
  });

  return result;
}
