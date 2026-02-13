import type { TreeItem } from '../stores/documentTreeStore';
import { isAuthenticated } from '../../auth/stores/googleAuthStore';
import { get } from 'svelte/store';

const API_BASE_URL = 'http://localhost:8000';

/**
 * Send document tree structure to the backend
 * @param documentTree The document tree structure
 * @param fileId The file ID
 * @param isTemporary Whether the file is temporary (not saved to Google Drive)
 */
export async function sendDocumentTree(
    documentTree: TreeItem[], 
    fileId?: string, 
    isTemporary?: boolean
): Promise<void> {
    // Skip sending document tree for temporary files or when not authenticated
    if (isTemporary || !get(isAuthenticated)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/document/tree`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_tree: documentTree,
                file_id: fileId
            })
        });
        
        if (!response.ok) {
            console.error('Failed to send document tree to backend:', response.statusText);
        }
    } catch (error: unknown) {
        console.error('Error sending document tree to backend:', error);
    }
}
