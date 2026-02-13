import { writable } from 'svelte/store';
import { sendDocumentTree } from '../services/documentTreeApi';
import { activeFile } from './fileStore';
import { get } from 'svelte/store';

// Define the tree item interface
export interface TreeItem {
  id: string;
  level: number;
  text: string;
  position: number;
  children: TreeItem[];
}

// Create a writable store for the document tree
export const documentTree = writable<TreeItem[]>([]);

// Create a writable store for document tree visibility
export const documentTreeVisible = writable<boolean>(false);

// Set up subscription to send document tree to backend when it changes
documentTree.subscribe(treeItems => {
  if (treeItems.length > 0) {
    // Get the current file ID if available
    const currentFile = get(activeFile);
    const fileId = currentFile ? currentFile.id : undefined;
    const isTemporary = currentFile?.isTemporary || false;
    
    // Send the updated document tree to the backend
    sendDocumentTree(treeItems, fileId, isTemporary);
  }
});

// Function to update the document tree
export function updateDocumentTree(items: TreeItem[]) {
  documentTree.set(items);
}
