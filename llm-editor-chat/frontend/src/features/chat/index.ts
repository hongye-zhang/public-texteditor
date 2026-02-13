// Export components
export { default as ChatPanel } from './components/ChatPanel.svelte';
export { default as ChatMessage } from './components/ChatMessage.svelte';
export { default as ChatInput } from './components/ChatInput.svelte';

// Export services
export {
  uploadFile,
  streamChat,
  type ChatMessage as ChatMessageType,
  type FileUploadResponse,
  type StreamResponse
} from './services/chatApi';

// Export stores
// TODO: Add chat-related stores when they are created
