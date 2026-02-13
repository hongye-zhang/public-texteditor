import { type StreamResponse } from '../../chat/services/chatApi';

const API_BASE_URL = 'http://localhost:8000';

/**
 * Process streaming text modification requests
 */
export async function streamModifyText(
    message: string,
    selectedText: string,
    startPosition: number,
    endPosition: number,
    editorContent?: string,
    onChunk?: (chunk: StreamResponse) => void
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
        
        const response = await fetch(`${API_BASE_URL}/text/stream-modify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message,
                selected_text: selectedText,
                start_position: startPosition,
                end_position: endPosition,
                editor_content: editorContent
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
                    content: `Failed to stream modify text response: ${response ? response.statusText : 'Connection error'}`
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
                            console.warn('Failed to parse chunk:', e);
                        }
                    }
                }
            }
        } catch (streamError) {
            // Handle stream reading errors
            if (onChunk) {
                onChunk({
                    type: 'error',
                    content: `Error reading stream: ${streamError instanceof Error ? streamError.message : 'Unknown error'}`
                });
            }
        }
    } catch (error: any) {
        // Only log critical errors that weren't handled elsewhere
        if (error instanceof Error && error.name !== 'AbortError') {
            console.warn('Error in streamModifyText:', error);
        }
        
        if (onChunk) {
            onChunk({
                type: 'error',
                content: `Error: ${error.message || 'Unknown error'}`
            });
        }
    }
}
