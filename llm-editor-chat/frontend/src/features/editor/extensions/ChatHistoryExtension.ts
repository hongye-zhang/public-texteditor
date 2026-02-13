import { Extension } from '@tiptap/core';
import type { CommandProps } from '@tiptap/core';

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: string; // ISO date string
  attachment?: {
    type: string;
    name: string;
    url: string;
  };
  thinking?: boolean;
}

export interface ChatSession {
  id: string;
  name: string;
  createdAt: string; // ISO date string
  updatedAt: string; // ISO date string
  messages: ChatMessage[];
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    chatHistory: {
      /**
       * Add a new chat session
       */
      addChatSession: (session: ChatSession) => ReturnType;
      /**
       * Update an existing chat session
       */
      updateChatSession: (sessionId: string, session: Partial<ChatSession>) => ReturnType;
      /**
       * Add a message to a chat session
       */
      addMessageToSession: (sessionId: string, message: ChatMessage) => ReturnType;
      /**
       * Get all chat sessions
       */
      getChatSessions: () => ChatSession[];
      /**
       * Get a specific chat session
       */
      getChatSession: (sessionId: string) => ChatSession | undefined;
      /**
       * Remove a chat session
       */
      removeChatSession: (sessionId: string) => ReturnType;
      /**
       * Set the active chat session
       */
      setActiveChatSession: (sessionId: string) => ReturnType;
      /**
       * Get the active chat session ID
       */
      getActiveChatSessionId: () => string | null;
    };
  }
}

export const ChatHistory = Extension.create({
  name: 'chatHistory',

  addOptions() {
    return {
      defaultSessionName: 'Chat Session',
    };
  },

  addStorage() {
    return {
      sessions: [] as ChatSession[],
      activeSessionId: null as string | null,
    };
  },

  addCommands() {
    return {
      addChatSession:
        (session: ChatSession) => ({ editor }: CommandProps) => {
          const newSession = {
            ...session,
            createdAt: session.createdAt || new Date().toISOString(),
            updatedAt: session.updatedAt || new Date().toISOString(),
          };

          editor.storage.chatHistory.sessions = [
            ...editor.storage.chatHistory.sessions,
            newSession,
          ];

          // If this is the first session, make it active
          if (editor.storage.chatHistory.sessions.length === 1) {
            editor.storage.chatHistory.activeSessionId = newSession.id;
          }

          return true;
        },

      updateChatSession:
        (sessionId: string, sessionUpdates: Partial<ChatSession>) => ({ editor }: CommandProps) => {
          const sessionIndex = editor.storage.chatHistory.sessions.findIndex(
            (s: ChatSession) => s.id === sessionId
          );

          if (sessionIndex === -1) return false;

          const sessions = [...editor.storage.chatHistory.sessions];
          sessions[sessionIndex] = {
            ...sessions[sessionIndex],
            ...sessionUpdates,
            updatedAt: new Date().toISOString(),
          };

          editor.storage.chatHistory.sessions = sessions;

          return true;
        },

      addMessageToSession:
        (sessionId: string, message: ChatMessage) => ({ editor }: CommandProps) => {
          const sessionIndex = editor.storage.chatHistory.sessions.findIndex(
            (s: ChatSession) => s.id === sessionId
          );

          if (sessionIndex === -1) return false;

          const sessions = [...editor.storage.chatHistory.sessions];
          sessions[sessionIndex] = {
            ...sessions[sessionIndex],
            messages: [...sessions[sessionIndex].messages, message],
            updatedAt: new Date().toISOString(),
          };

          editor.storage.chatHistory.sessions = sessions;

          return true;
        },

      getChatSessions:
        () => ({ editor }: CommandProps) => {
          return [...editor.storage.chatHistory.sessions];
        },

      getChatSession:
        (sessionId: string) => ({ editor }: CommandProps) => {
          return editor.storage.chatHistory.sessions.find((s: ChatSession) => s.id === sessionId);
        },

      removeChatSession:
        (sessionId: string) => ({ editor }: CommandProps) => {
          editor.storage.chatHistory.sessions = editor.storage.chatHistory.sessions.filter(
            (s: ChatSession) => s.id !== sessionId
          );

          // If we removed the active session, set a new active session
          if (editor.storage.chatHistory.activeSessionId === sessionId) {
            editor.storage.chatHistory.activeSessionId = editor.storage.chatHistory.sessions.length > 0
              ? editor.storage.chatHistory.sessions[0].id
              : null;
          }

          return true;
        },

      setActiveChatSession:
        (sessionId: string) => ({ editor }: CommandProps) => {
          // Check if session exists
          const sessionExists = editor.storage.chatHistory.sessions.some(
            (s: ChatSession) => s.id === sessionId
          );

          if (!sessionExists) return false;

          editor.storage.chatHistory.activeSessionId = sessionId;
          return true;
        },

      getActiveChatSessionId:
        () => ({ editor }: CommandProps) => {
          return editor.storage.chatHistory.activeSessionId;
        },
    };
  },
});
