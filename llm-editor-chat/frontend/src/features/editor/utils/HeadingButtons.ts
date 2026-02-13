import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
import { Node } from 'prosemirror-model';

// 创建一个唯一的插件键
const headingButtonsPluginKey = new PluginKey('headingButtons');

// 存储折叠状态的类型
type FoldingState = Record<string, boolean>;

// 扩展类型
interface HeadingButtonsExtension {
  storage: {
    foldingState: FoldingState;
  };
}

export const HeadingButtons = Extension.create({
  name: 'headingButtons',

  addStorage() {
    return {
      // 存储每个标题的折叠状态
      foldingState: {} as FoldingState,
    };
  },

  addProseMirrorPlugins() {
    const extension = this as unknown as HeadingButtonsExtension;

    // 创建一个函数来生成装饰器
    const createDecorations = (doc: Node, extension: HeadingButtonsExtension) => {
      const decorations: Decoration[] = [];
      const { foldingState } = extension.storage;

      // 遍历文档中的所有节点
      doc.descendants((node: Node, pos: number) => {
        // 检查节点是否是标题
        if (node.type.name === 'heading') {
          // 生成唯一ID
          const headingId = `heading-${pos}`;
          const isFolded = foldingState[headingId] || false;
          
          // 创建一个按钮装饰器，添加到标题的末尾
          const button = document.createElement('span');
          button.className = 'heading-button';
          // 使用Font Awesome图标，更加美观且一致
          button.innerHTML = isFolded ? '<i class="fas fa-chevron-right"></i>' : '<i class="fas fa-chevron-down"></i>';
          button.contentEditable = 'false';
          button.setAttribute('aria-label', '折叠/展开');
          button.setAttribute('data-heading-id', headingId);
          
          // 添加装饰器到标题节点的末尾
          decorations.push(
            Decoration.widget(pos + node.nodeSize - 1, button, {
              key: `heading-button-${pos}`,
              // 确保按钮在标题文本之后
              side: 1,
            })
          );
        }
      });

      // 添加折叠内容的装饰器
      doc.descendants((node: Node, pos: number) => {
        if (node.type.name === 'heading') {
          const headingId = `heading-${pos}`;
          const isFolded = foldingState[headingId] || false;

          if (isFolded) {
            const level = node.attrs.level;
            const endPos = pos + node.nodeSize;
            let foldEndPos = doc.content.size;
            
            // 查找下一个相同或更高级别的标题
            let scanPos = endPos;
            while (scanPos < doc.content.size) {
              const scanNode = doc.nodeAt(scanPos);
              if (scanNode && scanNode.type.name === 'heading' && scanNode.attrs.level <= level) {
                foldEndPos = scanPos;
                break;
              }
              
              if (!scanNode) {
                scanPos++;
              } else {
                scanPos += scanNode.nodeSize;
              }
            }
            
            // 为每个需要折叠的段落添加装饰器
            if (foldEndPos > endPos) {
              let contentPos = endPos;
              while (contentPos < foldEndPos) {
                const contentNode = doc.nodeAt(contentPos);
                if (contentNode) {
                  decorations.push(
                    Decoration.node(contentPos, contentPos + contentNode.nodeSize, {
                      class: 'folded-content'
                    })
                  );
                  contentPos += contentNode.nodeSize;
                } else {
                  contentPos++;
                }
              }
            }
          }
        }
      });

      return DecorationSet.create(doc, decorations);
    };

    return [
      new Plugin({
        key: headingButtonsPluginKey,
        state: {
          init(_, { doc }) {
            return createDecorations(doc, extension);
          },
          apply(tr, oldState) {
            // 如果文档发生变化或者有自定义元数据，重新计算装饰器
            if (tr.docChanged || tr.getMeta('updateFolding')) {
              return createDecorations(tr.doc, extension);
            }
            return oldState.map(tr.mapping, tr.doc);
          },
        },
        props: {
          decorations(state) {
            return this.getState(state);
          },
          handleDOMEvents: {
            click(view, event) {
              // 检查点击的元素是否是标题按钮或其子元素
              let target = event.target as HTMLElement;
              
              // 如果点击的是图标元素，获取其父元素
              if (target.tagName.toLowerCase() === 'i' && target.parentElement) {
                target = target.parentElement;
              }
              
              if (target && target.classList.contains('heading-button')) {
                // 阻止默认行为和冒泡
                event.preventDefault();
                event.stopPropagation();

                // 获取标题ID
                const headingId = target.getAttribute('data-heading-id');
                if (!headingId) return false;

                // 切换折叠状态
                const foldingState = extension.storage.foldingState;
                const isFolded = !foldingState[headingId];
                foldingState[headingId] = isFolded;

                // 更新按钮图标
                target.innerHTML = isFolded ? '<i class="fas fa-chevron-right"></i>' : '<i class="fas fa-chevron-down"></i>';
                
                // 调试信息
                console.log(`标题 ${headingId} 的折叠状态已更新为: ${isFolded ? '折叠' : '展开'}`);

                // 更新编辑器视图
                view.dispatch(view.state.tr.setMeta('updateFolding', true));
                
                return true;
              }
              return false;
            },
          },
        },
      }),
    ];
  },
});
