import { v4 as uuidv4 } from 'uuid';
import type { Editor } from '@tiptap/core';
import type { ChatMessage, ChatSession } from '../../editor/extensions/ChatHistoryExtension';

/**
 * ChatSessionManager provides an interface to manage chat sessions and messages
 * stored directly in the Tiptap document via the ChatHistory extension.
 */
export class ChatSessionManager {
  private editor: Editor;
  private activeSessionId: string | null = null;

  constructor(editor: Editor) {
    this.editor = editor;
    this.initializeActiveSession();
  }

  /**
   * Initialize the active session from the editor or create a new one if none exists
   */
  private initializeActiveSession(): void {
    // Get active session ID from the editor
    this.activeSessionId = this.editor.commands.getActiveChatSessionId();
    
    // If no active session, check if there are any sessions
    if (!this.activeSessionId) {
      const sessions = this.getSessions();
      
      if (sessions.length > 0) {
        // Use the first session as active
        this.activeSessionId = sessions[0].id;
        this.editor.commands.setActiveChatSession(this.activeSessionId);
      } else {
        // Create a default session if none exists
        this.createNewSession('Default Chat');
      }
    }
  }

  /**
   * Get all chat sessions from the document
   */
  getSessions(): ChatSession[] {
    return this.editor.commands.getChatSessions();
  }

  /**
   * Get the active chat session
   */
  getActiveSession(): ChatSession | undefined {
    if (!this.activeSessionId) return undefined;
    return this.editor.commands.getChatSession(this.activeSessionId);
  }

  /**
   * Get messages from the active chat session
   */
  getMessages(): ChatMessage[] {
    const activeSession = this.getActiveSession();
    return activeSession ? [...activeSession.messages] : [];
  }

  /**
   * Create a new chat session
   */
  createNewSession(name: string = 'New Chat'): string {
    const sessionId = uuidv4();
    
    this.editor.commands.addChatSession({
      id: sessionId,
      name,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: []
    });
    
    // Set as active session
    this.activeSessionId = sessionId;
    this.editor.commands.setActiveChatSession(sessionId);
    
    return sessionId;
  }

  /**
   * Set the active chat session
   */
  setActiveSession(sessionId: string): boolean {
    const success = this.editor.commands.setActiveChatSession(sessionId);
    if (success) {
      this.activeSessionId = sessionId;
    }
    return success;
  }

  /**
   * Add a message to the active chat session
   */
  addMessage(message: ChatMessage): boolean {
    if (!this.activeSessionId) {
      this.createNewSession();
    }
    
    return this.editor.commands.addMessageToSession(
      this.activeSessionId!, 
      message
    );
  }

  /**
   * Set all messages for the active chat session
   */
  setMessages(messages: ChatMessage[]): boolean {
    if (!this.activeSessionId) {
      this.createNewSession();
    }
    
    // Update the session with new messages
    return this.editor.commands.updateChatSession(
      this.activeSessionId!,
      {
        messages,
        updatedAt: new Date().toISOString()
      }
    );
  }

  /**
   * Rename the active chat session
   */
  renameActiveSession(name: string): boolean {
    if (!this.activeSessionId) return false;
    
    return this.editor.commands.updateChatSession(
      this.activeSessionId,
      {
        name,
        updatedAt: new Date().toISOString()
      }
    );
  }

  /**
   * Delete a chat session
   */
  deleteSession(sessionId: string): boolean {
    return this.editor.commands.removeChatSession(sessionId);
  }

  /**
   * Clear all messages in the active chat session
   */
  clearActiveSessionMessages(): boolean {
    if (!this.activeSessionId) return false;
    
    return this.editor.commands.updateChatSession(
      this.activeSessionId,
      {
        messages: [],
        updatedAt: new Date().toISOString()
      }
    );
  }
}
