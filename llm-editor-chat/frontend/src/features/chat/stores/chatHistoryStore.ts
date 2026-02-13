import { writable } from 'svelte/store';

export interface ChatMessageHistory {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
  attachment?: {
    type: string;
    name: string;
    url: string;
  };
  thinking?: boolean;
}

export interface DocumentChatHistory {
  documentId: string;
  messages: ChatMessageHistory[];
  lastUpdated: Date;
}

// Store for all document chat histories
const createChatHistoryStore = () => {
  // Initialize from localStorage if available
  let initialHistories: Record<string, DocumentChatHistory> = {};
  
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const storedHistories = localStorage.getItem('documentChatHistories');
      if (storedHistories) {
        // Parse the stored JSON and convert string dates back to Date objects
        const parsed = JSON.parse(storedHistories);
        Object.keys(parsed).forEach(docId => {
          initialHistories[docId] = {
            ...parsed[docId],
            lastUpdated: new Date(parsed[docId].lastUpdated),
            messages: parsed[docId].messages.map((msg: any) => ({
              ...msg,
              timestamp: new Date(msg.timestamp)
            }))
          };
        });
      }
    } catch (error) {
      console.error('Error loading chat histories from localStorage:', error);
    }
  }
  
  const { subscribe, update, set } = writable<Record<string, DocumentChatHistory>>(initialHistories);
  
  // Save to localStorage whenever the store changes
  const saveToLocalStorage = (histories: Record<string, DocumentChatHistory>) => {
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        localStorage.setItem('documentChatHistories', JSON.stringify(histories));
      } catch (error) {
        console.error('Error saving chat histories to localStorage:', error);
      }
    }
  };
  
  return {
    subscribe,
    
    // Add a message to a document's chat history
    addMessage: (documentId: string, message: ChatMessageHistory) => {
      update(histories => {
        const docHistory = histories[documentId] || {
          documentId,
          messages: [],
          lastUpdated: new Date()
        };
        
        const updatedHistory = {
          ...docHistory,
          messages: [...docHistory.messages, message],
          lastUpdated: new Date()
        };
        
        const result = { ...histories, [documentId]: updatedHistory };
        saveToLocalStorage(result);
        return result;
      });
    },
    
    // Update a specific message in a document's history
    updateMessage: (documentId: string, messageId: string, updates: Partial<ChatMessageHistory>) => {
      update(histories => {
        if (!histories[documentId]) return histories;
        
        const updatedMessages = histories[documentId].messages.map(msg => 
          msg.id === messageId ? { ...msg, ...updates } : msg
        );
        
        const updatedHistory = {
          ...histories[documentId],
          messages: updatedMessages,
          lastUpdated: new Date()
        };
        
        const result = { ...histories, [documentId]: updatedHistory };
        saveToLocalStorage(result);
        return result;
      });
    },
    
    // Set all messages for a document
    setDocumentMessages: (documentId: string, messages: ChatMessageHistory[]) => {
      update(histories => {
        const updatedHistory = {
          documentId,
          messages,
          lastUpdated: new Date()
        };
        
        const result = { ...histories, [documentId]: updatedHistory };
        saveToLocalStorage(result);
        return result;
      });
    },
    
    // Clear history for a specific document
    clearDocumentHistory: (documentId: string) => {
      update(histories => {
        const { [documentId]: _, ...rest } = histories;
        saveToLocalStorage(rest);
        return rest;
      });
    },
    
    // Clear all histories (useful for logout or reset)
    clearAllHistories: () => {
      set({});
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.removeItem('documentChatHistories');
      }
    }
  };
};

export const chatHistoryStore = createChatHistoryStore();
