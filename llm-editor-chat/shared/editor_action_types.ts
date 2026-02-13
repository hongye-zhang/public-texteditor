/**
 * 编辑器动作类型定义
 * 基于共享的 editor_actions.json 文件自动生成
 */

// 导入 JSON 定义
// @ts-ignore - 忽略JSON导入错误
import actionDefinitions from './editor_actions.json';

// 定义动作类型枚举
export const EditorActionType: Record<string, string> = {};

// 从 JSON 定义动态生成枚举
Object.entries(actionDefinitions.actions).forEach(([key, value]: [string, any]) => {
  EditorActionType[key.toUpperCase()] = value.type;
});

// 为了类型安全，创建一个静态的类型对象
export type EditorActionTypeValues = typeof EditorActionType[keyof typeof EditorActionType];

// 基础动作接口
export interface EditorAction {
  type: string;
  payload: {
    // Base payload may vary per action; 'content' not required for all actions
    partial?: boolean;
    [key: string]: any;
  };
}

// 定义具体的动作类型接口
export interface InsertTextAction extends EditorAction {
  type: typeof EditorActionType.INSERT_TEXT;
  payload: {
    content: string;
    position?: 'cursor' | 'start' | 'end';
    partial?: boolean;
  };
}

export interface ReplaceTextAction extends EditorAction {
  type: typeof EditorActionType.REPLACE_TEXT;
  payload: {
    content: string;
    start: number;
    end: number;
    partial?: boolean;
  };
}

export interface DeleteTextAction extends EditorAction {
  type: typeof EditorActionType.DELETE_TEXT;
  payload: {
    start: number;
    end: number;
    partial?: boolean;
  };
}

export interface ReplaceAllAction extends EditorAction {
  type: typeof EditorActionType.REPLACE_ALL;
  payload: {
    content: string;
    partial?: boolean;
  };
}

// 验证动作类型是否有效
export function isValidActionType(type: string): boolean {
  const validTypes = Object.values(actionDefinitions.actions).map((a: any) => a.type);
  return validTypes.includes(type);
}

// 验证动作对象是否有效
export function isValidAction(action: any): boolean {
  if (!action || typeof action !== 'object' || !action.type || !action.payload) {
    return false;
  }
  
  // 检查类型是否有效
  if (!isValidActionType(action.type)) {
    return false;
  }
  
  // 获取该类型动作的定义
  const actionKey = Object.keys(actionDefinitions.actions).find(
    (key: string) => (actionDefinitions.actions as any)[key].type === action.type
  );
  
  if (!actionKey) {
    return false;
  }
  
  // 验证payload是否符合schema
  const schema = (actionDefinitions.actions as any)[actionKey].payload_schema;
  const payload = action.payload;
  
  // 检查必填字段
  for (const [field, type] of Object.entries(schema)) {
    // 可选字段以?结尾
    const isOptional = (type as string).endsWith('?');
    const baseType = isOptional ? (type as string).slice(0, -1) : type as string;
    
    // 如果字段不存在且不是可选的，则无效
    if (!(field in payload) && !isOptional) {
      return false;
    }
    
    // 如果字段存在，检查类型
    if (field in payload) {
      if (baseType === 'string' && typeof payload[field] !== 'string') {
        return false;
      } else if (baseType === 'number' && typeof payload[field] !== 'number') {
        return false;
      } else if (baseType === 'boolean' && typeof payload[field] !== 'boolean') {
        return false;
      }
    }
  }
  
  return true;
}

// 创建动作的辅助函数
export function createAction(type: string, payload: any): EditorAction {
  if (!isValidActionType(type)) {
    throw new Error(`Invalid action type: ${type}`);
  }
  
  return {
    type,
    payload
  };
}

// 特定动作类型的创建函数
export function createInsertTextAction(
  content: string,
  position: 'cursor' | 'start' | 'end' = 'cursor',
  partial: boolean = false
): EditorAction {
  return createAction(EditorActionType.INSERT_TEXT, { content, position, partial });
}

export function createReplaceTextAction(content: string, start: number, end: number, partial: boolean = false): EditorAction {
  return createAction(EditorActionType.REPLACE_TEXT, { content, start, end, partial });
}

export function createDeleteTextAction(
  start: number,
  end: number,
  partial: boolean = false
): EditorAction {
  return createAction(EditorActionType.DELETE_TEXT, { start, end, partial });
}

export function createReplaceAllAction(content: string, partial: boolean = false): EditorAction {
  return createAction(EditorActionType.REPLACE_ALL, { content, partial });
}
