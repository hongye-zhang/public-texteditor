import { writable, derived, get } from 'svelte/store';
import type { Editor } from '@tiptap/core';

// 保存触发类型
export enum SaveTriggerType {
  USER_INPUT = 'user_input',
  AI_CONTENT = 'ai_content',
  PERIODIC = 'periodic',
  FILE_SWITCH = 'file_switch',
  WINDOW_BLUR = 'window_blur',
  APP_CLOSE = 'app_close',
  MANUAL = 'manual'
}

// 保存状态
export enum SaveState {
  IDLE = 'idle',
  PENDING = 'pending',
  SAVING = 'saving',
  SUCCESS = 'success',
  ERROR = 'error',
  RETRYING = 'retrying'
}

// 保存配置
export interface AutoSaveConfig {
  userInputDelay: number;      // 用户输入延迟 (ms)
  aiContentDelay: number;      // AI内容延迟 (ms)
  periodicInterval: number;    // 定期保存间隔 (ms)
  maxRetries: number;          // 最大重试次数
  retryDelay: number;          // 重试延迟 (ms)
  enabled: boolean;            // 是否启用自动保存
}

// 保存任务
interface SaveTask {
  id: string;
  triggerType: SaveTriggerType;
  content: string;
  editorState: any;
  timestamp: number;
  priority: number;
  retryCount: number;
}

// 保存结果
interface SaveResult {
  success: boolean;
  error?: Error;
  timestamp: number;
  duration: number;
}

export class AutoSaveManager {
  private editor: Editor | null = null;
  private config: AutoSaveConfig;
  private saveQueue: SaveTask[] = [];
  private currentTask: SaveTask | null = null;
  private timers: Map<string, ReturnType<typeof setTimeout>> = new Map();
  private lastSaveContent: string = '';
  private lastSaveTime: number = 0;
  private saveCallback: ((content: string, state: any) => Promise<void>) | null = null;

  // Svelte stores
  public readonly state = writable<SaveState>(SaveState.IDLE);
  public readonly lastSaved = writable<number>(0);
  public readonly hasUnsavedChanges = writable<boolean>(false);
  public readonly errorMessage = writable<string>('');

  constructor(config: Partial<AutoSaveConfig> = {}) {
    this.config = {
      userInputDelay: 2000,
      aiContentDelay: 500,
      periodicInterval: 30000,
      maxRetries: 3,
      retryDelay: 1000,
      enabled: true,
      ...config
    };

    this.setupPeriodicSave();
    this.setupWindowEvents();
  }

  // 初始化编辑器
  public initEditor(editor: Editor, saveCallback: (content: string, state: any) => Promise<void>) {
    this.editor = editor;
    this.saveCallback = saveCallback;
    this.setupEditorEvents();
  }

  // 设置编辑器事件监听
  private setupEditorEvents() {
    if (!this.editor) return;

    // 监听内容更新
    this.editor.on('update', ({ editor }) => {
      this.handleContentChange(SaveTriggerType.USER_INPUT);
    });

    // 监听选择变化（用于LaTeX等特殊内容）
    this.editor.on('selectionUpdate', ({ editor }) => {
      const selection = editor.state.selection;
      if (selection && !selection.empty) {
        this.handleContentChange(SaveTriggerType.USER_INPUT);
      }
    });
  }

  // 设置定期保存
  private setupPeriodicSave() {
    if (!this.config.enabled) return;

    const periodicTimer = setInterval(() => {
      if (this.hasContentChanged()) {
        this.scheduleSave(SaveTriggerType.PERIODIC);
      }
    }, this.config.periodicInterval);

    this.timers.set('periodic', periodicTimer);
  }

  // 设置窗口事件
  private setupWindowEvents() {
    // 窗口失焦时保存
    window.addEventListener('blur', () => {
      if (this.hasContentChanged()) {
        this.scheduleSave(SaveTriggerType.WINDOW_BLUR);
      }
    });

    // 页面卸载前保存
    window.addEventListener('beforeunload', (event) => {
      if (this.hasContentChanged()) {
        this.forceSave(SaveTriggerType.APP_CLOSE);
        event.preventDefault();
        event.returnValue = '您有未保存的更改，确定要离开吗？';
      }
    });
  }

  // 处理内容变化
  private handleContentChange(triggerType: SaveTriggerType) {
    if (!this.config.enabled || !this.hasContentChanged()) return;

    this.hasUnsavedChanges.set(true);
    this.scheduleSave(triggerType);
  }

  // 检查内容是否发生变化
  private hasContentChanged(): boolean {
    if (!this.editor) return false;

    const currentContent = this.editor.getHTML();
    return currentContent !== this.lastSaveContent;
  }

  // 调度保存任务
  public scheduleSave(triggerType: SaveTriggerType, priority: number = 0) {
    if (!this.config.enabled || !this.editor || !this.saveCallback) return;

    const delay = this.getSaveDelay(triggerType);
    const timerId = `save_${triggerType}`;

    // 清除之前的定时器
    if (this.timers.has(timerId)) {
      clearTimeout(this.timers.get(timerId)!);
    }

    // 设置新的定时器
    const timer = setTimeout(() => {
      this.executeSave(triggerType, priority);
      this.timers.delete(timerId);
    }, delay);

    this.timers.set(timerId, timer);
    this.state.set(SaveState.PENDING);
  }

  // 获取保存延迟
  private getSaveDelay(triggerType: SaveTriggerType): number {
    switch (triggerType) {
      case SaveTriggerType.AI_CONTENT:
        return this.config.aiContentDelay;
      case SaveTriggerType.USER_INPUT:
        return this.config.userInputDelay;
      case SaveTriggerType.FILE_SWITCH:
      case SaveTriggerType.WINDOW_BLUR:
      case SaveTriggerType.APP_CLOSE:
      case SaveTriggerType.MANUAL:
        return 0; // 立即执行
      default:
        return this.config.userInputDelay;
    }
  }

  // 执行保存
  private async executeSave(triggerType: SaveTriggerType, priority: number = 0) {
    if (!this.editor || !this.saveCallback) return;

    const content = this.editor.getHTML();
    const editorState = this.editor.getJSON();

    const task: SaveTask = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      triggerType,
      content,
      editorState,
      timestamp: Date.now(),
      priority,
      retryCount: 0
    };

    // 添加到队列或立即执行
    if (this.currentTask) {
      this.addToQueue(task);
    } else {
      await this.processSaveTask(task);
    }
  }

  // 添加任务到队列
  private addToQueue(task: SaveTask) {
    // 按优先级和时间戳排序
    this.saveQueue.push(task);
    this.saveQueue.sort((a, b) => {
      if (a.priority !== b.priority) {
        return b.priority - a.priority; // 高优先级在前
      }
      return a.timestamp - b.timestamp; // 早的任务在前
    });
  }

  // 处理保存任务
  private async processSaveTask(task: SaveTask) {
    this.currentTask = task;
    this.state.set(SaveState.SAVING);

    try {
      const startTime = Date.now();
      await this.saveCallback!(task.content, task.editorState);
      
      const duration = Date.now() - startTime;
      this.handleSaveSuccess(task, duration);
    } catch (error) {
      this.handleSaveError(task, error as Error);
    }
  }

  // 处理保存成功
  private handleSaveSuccess(task: SaveTask, duration: number) {
    this.lastSaveContent = task.content;
    this.lastSaveTime = task.timestamp;
    this.lastSaved.set(task.timestamp);
    this.hasUnsavedChanges.set(false);
    this.state.set(SaveState.SUCCESS);
    this.errorMessage.set('');

    console.log(`保存成功 [${task.triggerType}] 耗时: ${duration}ms`);

    // 处理下一个任务
    this.processNextTask();
  }

  // 处理保存错误
  private async handleSaveError(task: SaveTask, error: Error) {
    console.error(`保存失败 [${task.triggerType}]:`, error);

    if (task.retryCount < this.config.maxRetries) {
      // 重试
      task.retryCount++;
      this.state.set(SaveState.RETRYING);
      
      setTimeout(() => {
        this.processSaveTask(task);
      }, this.config.retryDelay * task.retryCount);
    } else {
      // 重试次数用尽，标记为错误
      this.state.set(SaveState.ERROR);
      this.errorMessage.set(`保存失败: ${error.message}`);
      this.processNextTask();
    }
  }

  // 处理下一个任务
  private processNextTask() {
    this.currentTask = null;

    if (this.saveQueue.length > 0) {
      const nextTask = this.saveQueue.shift()!;
      this.processSaveTask(nextTask);
    } else {
      this.state.set(SaveState.IDLE);
    }
  }

  // 强制保存（同步）
  public forceSave(triggerType: SaveTriggerType = SaveTriggerType.MANUAL): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.editor || !this.saveCallback) {
        reject(new Error('编辑器或保存回调未初始化'));
        return;
      }

      const content = this.editor.getHTML();
      const editorState = this.editor.getJSON();

      this.saveCallback(content, editorState)
        .then(() => {
          this.lastSaveContent = content;
          this.lastSaveTime = Date.now();
          this.lastSaved.set(this.lastSaveTime);
          this.hasUnsavedChanges.set(false);
          this.state.set(SaveState.SUCCESS);
          console.log(`强制保存成功 [${triggerType}]`);
          resolve();
        })
        .catch((error) => {
          this.state.set(SaveState.ERROR);
          this.errorMessage.set(`强制保存失败: ${error.message}`);
          console.error(`强制保存失败 [${triggerType}]:`, error);
          reject(error);
        });
    });
  }

  // AI内容保存（高优先级）
  public saveAIContent() {
    this.scheduleSave(SaveTriggerType.AI_CONTENT, 10);
  }

  // 文件切换时保存
  public saveOnFileSwitch() {
    if (this.hasContentChanged()) {
      this.scheduleSave(SaveTriggerType.FILE_SWITCH, 5);
    }
  }

  // 更新配置
  public updateConfig(newConfig: Partial<AutoSaveConfig>) {
    this.config = { ...this.config, ...newConfig };
    
    // 重新设置定期保存
    if (this.timers.has('periodic')) {
      clearInterval(this.timers.get('periodic')!);
      this.timers.delete('periodic');
    }
    this.setupPeriodicSave();
  }

  // 启用/禁用自动保存
  public setEnabled(enabled: boolean) {
    this.config.enabled = enabled;
    if (!enabled) {
      // 清除所有定时器
      this.timers.forEach((timer) => clearTimeout(timer));
      this.timers.clear();
      this.state.set(SaveState.IDLE);
    } else {
      this.setupPeriodicSave();
    }
  }

  // 获取保存统计信息
  public getStats() {
    return {
      lastSaveTime: this.lastSaveTime,
      queueLength: this.saveQueue.length,
      currentTask: this.currentTask?.triggerType || null,
      hasUnsavedChanges: get(this.hasUnsavedChanges),
      state: get(this.state)
    };
  }

  // 清理资源
  public destroy() {
    // 清除所有定时器
    this.timers.forEach((timer) => clearTimeout(timer));
    this.timers.clear();

    // 移除事件监听
    // 注意：由于事件监听器是在setupWindowEvents中使用匿名函数注册的，
    // 所以无法直接移除。在实际应用中，这些事件监听器会随着页面卸载而自动清理

    // 清理编辑器事件
    if (this.editor) {
      this.editor.off('update');
      this.editor.off('selectionUpdate');
    }
  }
}

// 创建全局自动保存管理器实例
export const autoSaveManager = new AutoSaveManager();
