<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { get } from 'svelte/store';
  import type { Editor } from '@tiptap/core';
  import { documentTree, updateDocumentTree, type TreeItem } from '../stores/documentTreeStore';

  // Props
  export let editor: Editor | null = null;
  
  // State
  let treeItems: TreeItem[] = [];
  let unsubscribe: (() => void) | null = null;

  // Types
  interface TreeItem {
    id: string;
    level: number;
    text: string;
    position: number;
    children: TreeItem[];
  }

  // Parse document structure from editor content
  function parseDocumentStructure(): TreeItem[] {
    if (!editor) return [];
    
    const doc = editor.state.doc;
    const items: TreeItem[] = [];
    const stack: TreeItem[] = [];
    
    // Traverse the document to find headings
    doc.descendants((node, pos) => {
      if (node.type.name === 'heading') {
        const level = node.attrs.level;
        const id = `heading-${pos}`;
        
        // Get text content of the heading
        let text = '';
        node.forEach(child => {
          if (child.isText) {
            text += child.text;
          }
        });
        
        const newItem: TreeItem = {
          id,
          level,
          text,
          position: pos,
          children: []
        };
        
        // Find the correct parent in the hierarchy
        while (stack.length > 0 && stack[stack.length - 1].level >= level) {
          stack.pop();
        }
        
        if (stack.length === 0) {
          // This is a top-level heading
          items.push(newItem);
        } else {
          // This is a child of the last item in the stack
          stack[stack.length - 1].children.push(newItem);
        }
        
        // Add this item to the stack
        stack.push(newItem);
      }
    });
    
    return items;
  }

  // Handle click on a tree item
  function handleItemClick(position: number) {
    if (!editor) return;
    
    // Set cursor position to the heading
    editor.commands.setTextSelection(position + 1);
    editor.commands.focus();
  }

  // Update tree when editor content changes
  function updateTree() {
    if (!editor) {
      console.log("Cannot update tree: editor is null");
      return;
    }
    
    console.log("Updating document tree with editor:", editor);
    treeItems = parseDocumentStructure();
    // Update the store with the current tree structure
    updateDocumentTree(treeItems);
  }

  // Initialize and clean up
  onMount(() => {
    console.log("DocumentTree mounted, editor:", editor);
    if (editor) {
      updateTree();
      
      // Subscribe to editor updates
      unsubscribe = editor.on('update', () => {
        updateTree();
      });
    }
  });

  // Watch for changes to the editor prop
  $: if (editor) {
    console.log("Editor changed in DocumentTree:", editor);
    updateTree();
    
    // Clean up previous subscription if it exists
    if (unsubscribe) {
      unsubscribe();
    }
    
    // Create new subscription
    unsubscribe = editor.on('update', () => {
      updateTree();
    });
  }

  onDestroy(() => {
    if (unsubscribe) {
      unsubscribe();
    }
  });
</script>

<div class="document-tree">
  <h3 class="tree-title">Document Structure</h3>
  
  {#if treeItems.length === 0}
    <div class="empty-tree">No headings found in document</div>
  {:else}
    <ul class="tree-root">
      {#each treeItems as item}
        <li>
          <div 
            class="tree-item" 
            on:click={() => handleItemClick(item.position)}
            on:keydown={(e) => e.key === 'Enter' && handleItemClick(item.position)}
            tabindex="0"
            role="button"
            aria-label="Navigate to heading: ${item.text || 'Untitled Heading'}"
          >
            {item.text || 'Untitled Heading'}
          </div>
          
          {#if item.children.length > 0}
            <ul class="tree-children">
              {#each item.children as child}
                <li>
                  <div 
                    class="tree-item" 
                    on:click={() => handleItemClick(child.position)}
                    on:keydown={(e) => e.key === 'Enter' && handleItemClick(child.position)}
                    tabindex="0"
                    role="button"
                    aria-label="Navigate to heading: ${child.text || 'Untitled Heading'}"
                  >
                    {child.text || 'Untitled Heading'}
                  </div>
                  
                  {#if child.children.length > 0}
                    <ul class="tree-children">
                      {#each child.children as grandchild}
                        <li>
                          <div 
                            class="tree-item" 
                            on:click={() => handleItemClick(grandchild.position)}
                            on:keydown={(e) => e.key === 'Enter' && handleItemClick(grandchild.position)}
                            tabindex="0"
                            role="button"
                            aria-label="Navigate to heading: ${grandchild.text || 'Untitled Heading'}"
                          >
                            {grandchild.text || 'Untitled Heading'}
                          </div>
                          
                          {#if grandchild.children.length > 0}
                            <div class="more-children">+{grandchild.children.length} more</div>
                          {/if}
                        </li>
                      {/each}
                    </ul>
                  {/if}
                </li>
              {/each}
            </ul>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .document-tree {
    width: 100%;
    background-color: #f9f9f9;
    border-radius: 4px;
    padding: 10px;
    max-height: 400px;
    overflow-y: auto;
  }
  
  .tree-title {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 10px;
    padding-bottom: 5px;
    border-bottom: 1px solid #eaeaea;
  }
  
  .empty-tree {
    color: #888;
    font-style: italic;
    padding: 10px 0;
  }
  
  .tree-root {
    list-style-type: none;
    padding-left: 0;
    margin: 0;
  }
  
  .tree-children {
    list-style-type: none;
    padding-left: 20px;
    margin: 0;
  }
  
  .tree-item {
    padding: 5px 8px;
    margin: 2px 0;
    cursor: pointer;
    border-radius: 3px;
    transition: background-color 0.2s;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }
  
  .tree-item:hover {
    background-color: #e9e9e9;
  }
  
  .more-children {
    padding: 3px 8px;
    margin-left: 20px;
    font-size: 0.8rem;
    color: #666;
    font-style: italic;
  }
  
  /* Scrollbar styles */
  .document-tree::-webkit-scrollbar {
    width: 3px;
    height: 3px;
  }
  
  .document-tree::-webkit-scrollbar-thumb {
    background-color: rgba(0, 0, 0, 0.15);
    border-radius: 1.5px;
  }
  
  .document-tree::-webkit-scrollbar-track {
    background-color: rgba(0, 0, 0, 0.03);
    border-radius: 1.5px;
  }
</style>
