// Define the API base URL (or import from a shared config)
const API_BASE_URL = 'http://localhost:8000';

// Chat-related interfaces
export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    id: string;
    timestamp: number;
    files?: File[];
}

export interface FileUploadResponse {
    file_path: string;
    filename: string;
}

import { logger } from '../../../lib/debug/logger';

export interface StreamResponse {
    type: 'thinking' | 'message' | 'action' | 'error' | 'stream';
    content: string;
    action?: {
        type: string;
        payload: any;
    };
}

export interface ChatHistoryItem {
    sender: string;
    content: string;
}

// Single file upload function
export async function uploadFile(file: File): Promise<FileUploadResponse> {
    try {
        logger.debug(`Uploading file to ${API_BASE_URL}`);
        
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/chat/upload-file`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            logger.error('File upload error:', response.status, errorText);
            throw new Error(`Upload failed: ${errorText}`);
        }
        
        return await response.json();
    } catch (error: unknown) {
        logger.error('Error uploading file:', error);
        throw error instanceof Error ? error : new Error('Unknown error during file upload');
    }
}

// Multiple files upload function
export async function uploadFiles(files: File[]): Promise<FileUploadResponse[]> {
    try {
        logger.debug(`Uploading ${files.length} files`);
        
        const formData = new FormData();
        
        // 添加所有文件到FormData
        files.forEach((file, index) => {
            formData.append('files', file);
        });
        
        const response = await fetch(`${API_BASE_URL}/chat/upload-files`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            logger.error('Multiple files upload error:', response.status, errorText);
            throw new Error(`Upload failed: ${errorText}`);
        }
        
        return await response.json();
    } catch (error: unknown) {
        logger.error('Error uploading multiple files:', error);
        throw error instanceof Error ? error : new Error('Unknown error during multiple files upload');
    }
}

/**
 * 处理流式聊天请求
 */
export async function streamChat(
    message: string, 
    editorContent?: string, 
    selectedText?: string,
    filePath?: string | string[],  // 可以是单个文件路径或JSON字符串形式的文件路径数组
    selectedNodesInfo?: any[],
    selectionStart?: number,
    selectionEnd?: number,
    documentWordCount?: number,
    documentCharCount?: number,
    onChunk?: (chunk: StreamResponse) => void,
    chatHistory?: Array<ChatHistoryItem>,
    systemPrompt?: string,
    modelId?: string,
    apiKey?: string
): Promise<void> {
    try {
        // Check if backend is available first
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000);
            
            const checkResponse = await fetch(`${API_BASE_URL}/health`, {
                method: 'GET',
                signal: controller.signal
            }).catch(() => null);
            
            clearTimeout(timeoutId);
            
            if (!checkResponse || !checkResponse.ok) {
                if (onChunk) {
                    onChunk({
                        type: 'error',
                        content: 'Backend service is not available. Please make sure the server is running.'
                    });
                }
                return;
            }
        } catch (connectionError) {
            // Handle connection errors silently but notify the user
            if (onChunk) {
                onChunk({
                    type: 'error',
                    content: 'Could not connect to the backend service. Please check your connection.'
                });
            }
            return;
        }
        
        // 获取编辑器内容的 JSON 格式（如果可用）
        let editorContentJson = null;
        let editorContentHtml = null;
        
        if (editorContent) {
            // 检查是否已经是 JSON 字符串
            try {
                // 尝试解析 - 如果是有效的 JSON，这不会抛出错误
                JSON.parse(editorContent);
                // 如果没有抛出错误，说明已经是 JSON 字符串
                editorContentJson = editorContent;
                logger.debug('编辑器内容已经是 JSON 格式');
            } catch (e) {
                // 不是 JSON 格式，假设是 HTML
                editorContentHtml = editorContent;
                logger.debug('编辑器内容是 HTML 格式');
            }
        }
        
        // Only send API key for non-default models (like Claude)
        // For default OpenAI models, use the server's API key
        const defaultModels = ["gpt-4o", "gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"];
        const isDefaultModel = !modelId || defaultModels.includes(modelId);
        
        // Only include API key in headers for non-default models
        const headers = {
            'Content-Type': 'application/json',
            ...(!isDefaultModel && apiKey ? { 'X-API-Key': apiKey } : {})
        };
        
        logger.debug(`Using model: ${modelId || 'default'}, sending API key: ${!isDefaultModel && apiKey ? 'yes' : 'no'}`);
        
        const response = await fetch(`${API_BASE_URL}/chat/stream`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                message,
                editor_content: editorContentJson,
                editor_content_html: editorContentHtml,
                selected_text: selectedText,
                file_path: filePath,
                selected_nodes_info: selectedNodesInfo,
                selection_start: selectionStart,
                selection_end: selectionEnd,
                document_word_count: documentWordCount,
                document_char_count: documentCharCount,
                chat_history: chatHistory,
                system_prompt: systemPrompt,
                model_id: modelId,
                api_key: !isDefaultModel ? apiKey : undefined
            })
        }).catch(error => {
            // Handle fetch errors silently
            if (onChunk) {
                onChunk({
                    type: 'error',
                    content: `Connection error: ${error instanceof Error ? error.message : 'Unknown error'}`
                });
            }
            return null;
        });
        
        if (!response || !response.ok) {
            if (onChunk) {
                onChunk({
                    type: 'error',
                    content: `Failed to stream chat response: ${response ? response.statusText : 'Connection error'}`
                });
            }
            return;
        }
        
        const reader = response.body?.getReader();
        if (!reader) {
            if (onChunk) {
                onChunk({
                    type: 'error',
                    content: 'Failed to get response reader'
                });
            }
            return;
        }
        
        const decoder = new TextDecoder();
        let buffer = '';
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;
                const parts = buffer.split('\n\n');
                buffer = parts.pop() || '';
                for (const line of parts) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6)) as StreamResponse;
                            if (onChunk) onChunk(data);
                        } catch (e) {
                            logger.warn('Failed to parse chunk:', e, line);
                        }
                    }
                }
            }
        } catch (streamError) {
            // Handle stream reading errors
            logger.error('Error reading stream:', streamError);
            if (onChunk) {
                onChunk({
                    type: 'error',
                    content: `Error reading stream: ${streamError instanceof Error ? streamError.message : 'Unknown error'}`
                });
            }
        }
    } catch (error: unknown) {
        // Only log critical errors that weren't handled elsewhere
        if (error instanceof Error && error.name !== 'AbortError') {
            logger.warn('Error in streamChat:', error);
        }
        
        if (onChunk) {
            onChunk({
                type: 'error',
                content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
            });
        }
    }
}