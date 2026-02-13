<script lang="ts">
  import { onMount } from 'svelte';
  import DocumentTree from './DocumentTree.svelte';
  import type { Editor } from '@tiptap/core';
  
  // Props
  export let editor: Editor | null = null;
  export let visible: boolean = false;
</script>

<div class="document-tree-sidebar" class:visible>
  <div class="sidebar-header">
    <h2>Document Structure</h2>
    <button class="close-button" on:click={() => visible = false}>
      <i class="fas fa-times"></i>
    </button>
  </div>
  
  <div class="sidebar-content">
    <DocumentTree {editor} />
  </div>
</div>

<style>
  .document-tree-sidebar {
    position: absolute;
    top: 0;
    right: -300px;
    width: 280px;
    height: 100%;
    background-color: white;
    box-shadow: -2px 0 5px rgba(0, 0, 0, 0.1);
    transition: right 0.3s ease;
    z-index: 100;
    display: flex;
    flex-direction: column;
  }
  
  .document-tree-sidebar.visible {
    right: 0;
  }
  
  .sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 15px;
    border-bottom: 1px solid #eaeaea;
  }
  
  .sidebar-header h2 {
    font-size: 1.1rem;
    margin: 0;
  }
  
  .close-button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1rem;
    color: #666;
    padding: 5px;
  }
  
  .close-button:hover {
    color: #333;
  }
  
  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
  }
</style>
