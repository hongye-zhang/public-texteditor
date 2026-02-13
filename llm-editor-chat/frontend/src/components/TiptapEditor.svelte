<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Editor } from '@tiptap/core';
  import StarterKit from '@tiptap/starter-kit';
  import Placeholder from '@tiptap/extension-placeholder';
  import Link from '@tiptap/extension-link';
  import Image from '@tiptap/extension-image';
  import Highlight from '@tiptap/extension-highlight';
  import Table from '@tiptap/extension-table';
  import TableRow from '@tiptap/extension-table-row';
  import TableCell from '@tiptap/extension-table-cell';
  import TableHeader from '@tiptap/extension-table-header';
  import { Markdown } from 'tiptap-markdown';
  import katex from 'katex';
  import 'katex/dist/katex.min.css';
  
  // Import our custom components
  import EditorToolbar from './editor/EditorToolbar.svelte';
  import EditorContent from './editor/EditorContent.svelte';
  import EditorFeedback from './editor/EditorFeedback.svelte';
  import SelectionMenu from './editor/SelectionMenu.svelte';
  import { InlineMath, BlockMath } from './editor/LaTeXExtensions';
  import { processLatexInPastedContent } from './editor/EditorUtils';
  import { HeadingButtons } from './editor/HeadingButtons';
  import { TextSelectionExtension } from './editor/TextSelectionExtension';
  
  // State variables
  export let editor: Editor | null = null;
  let element: HTMLElement | null = null;
  let editorInitialized = false;
  
  // Local storage key for editor content
  const EDITOR_STORAGE_KEY = 'tiptap-editor-content';
  
  // Export editor instance
  export function getEditor(): Editor | null {
    return editor;
  }
  
  // Handle editor content element ready
  function handleElementReady(event: CustomEvent<{ element: HTMLElement }>): void {
    element = event.detail.element;
    initEditor();
  }
  
  // Initialize editor
  function initEditor(): void {
    if (!element || editorInitialized) {
      return;
    }
    
    try {
      console.log('Initializing editor...');
      editor = new Editor({
        element: element,
        extensions: [
          StarterKit,
          Placeholder.configure({
            placeholder: 'Start writing or paste your content...',
          }),
          Link.configure({
            openOnClick: false,
          }),
          Image,
          Highlight,
          Table.configure({
            resizable: true,
          }),
          TableRow,
          TableCell,
          TableHeader,
          Markdown.configure({
            transformPastedText: true,
            transformCopiedText: true,
            html: true,
            tightLists: true,
            bulletListMarker: '-',
            linkify: true
          }),
          InlineMath,
          BlockMath,
          HeadingButtons,
          TextSelectionExtension,
        ],
        content: loadEditorContent() || '',
        editorProps: {
          handlePaste: (view, event) => {
            if (!editor) return false;
            
            const text = event.clipboardData?.getData('text/plain');
            if (!text) return false;
            
            // Check if LaTeX syntax is included
            const hasLatexSyntax = text.includes('$') || 
                                  text.includes('\\[') || 
                                  text.includes('\\]') ||
                                  text.includes('\\(') || 
                                  text.includes('\\)') ||
                                  text.includes('\\sqrt') ||
                                  text.includes('\\frac');
            
            if (hasLatexSyntax) {
              // Process LaTeX
              processLatexInPastedContent(editor, event);
              return true; // We've handled this event, don't continue processing
            }
            
            return false; // Let Tiptap handle regular text paste
          },
        },
      });
      
      // Mark editor as initialized
      editorInitialized = true;
      console.log('Editor initialized successfully');
      
      // Set up content change listener for auto-save
      editor.on('update', ({ editor }) => {
        saveEditorContent(editor.getHTML());
      });
      
      // Show success feedback
      if (window.editorFeedback) {
        window.editorFeedback.show('Editor is ready', '#07C160');
      }
    } catch (error) {
      console.error('Error initializing editor:', error);
      editorInitialized = false;
      
      // Show error feedback
      if (window.editorFeedback) {
        window.editorFeedback.show('Editor initialization failed', '#e74c3c');
      }
    }
  }
  
  // Cleanup
  onDestroy(() => {
    if (editor) {
      editor.destroy();
    }
  });
  
  // Get editor content
  export function getEditorContent(): string | null {
    if (!editor) return null;
    return editor.getHTML();
  }
  
  // Get editor Markdown content
  export function getEditorMarkdown(): string | null {
    if (!editor) return null;
    try {
      return editor.storage.markdown?.getMarkdown() || null;
    } catch (error) {
      console.error('Error getting Markdown:', error);
      return null;
    }
  }
  
  // Load content from localStorage
  function loadEditorContent(): string | null {
    try {
      if (typeof localStorage !== 'undefined') {
        const savedContent = localStorage.getItem(EDITOR_STORAGE_KEY);
        console.log('Loaded content from localStorage');
        return savedContent;
      }
      return null;
    } catch (error) {
      console.error('Error loading content from localStorage:', error);
      return null;
    }
  }
  
  // Save content to localStorage
  function saveEditorContent(content: string): void {
    try {
      if (typeof localStorage !== 'undefined' && content) {
        localStorage.setItem(EDITOR_STORAGE_KEY, content);
        console.log('Content saved to localStorage');
      }
    } catch (error) {
      console.error('Error saving content to localStorage:', error);
    }
  }
  
  // Clear content from localStorage
  export function clearEditorContent(): void {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(EDITOR_STORAGE_KEY);
        if (editor) {
          editor.commands.setContent('');
        }
        console.log('Content cleared from localStorage');
      }
    } catch (error) {
      console.error('Error clearing content from localStorage:', error);
    }
  }
  
  onMount(() => {
    console.log('TiptapEditor mounted');
  });
</script>

<div class="editor-container">
  <!-- Editor toolbar -->
  <EditorToolbar {editor} />
  
  <!-- Editor content area -->
  <EditorContent on:elementReady={handleElementReady} />
  
  <!-- Selection menu -->
  {#if editor}
    <SelectionMenu {editor} />
  {/if}
  
  <!-- Feedback message -->
  <EditorFeedback />
</div>

<style>
  .editor-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    overflow: hidden;
    background-color: white;
    box-shadow: none;
  }
  
  /* Tiptap editor styles */
  :global(.ProseMirror) {
    outline: none;
    height: calc(100% - 52px); /* subtract toolbar height */
    overflow-y: auto;
    padding: 1rem;
    max-height: calc(100vh - 250px);
    line-height: 1.75rem;
  }
  
  :global(.ProseMirror p) {
    margin-bottom: 0.75rem;
    line-height: 1.75rem;
  }
  
  :global(.ProseMirror h1) {
    font-size: 2.25em;
    font-weight: 700;
    letter-spacing: -.04rem;
    margin-bottom: 1rem;
    line-height: normal;
  }
  
  :global(.ProseMirror h2) {
    font-size: 1.5em;
    font-weight: 600;
    margin-bottom: 1rem;
    margin-top: 2rem;
    line-height: normal;
  }
  
  :global(.ProseMirror h3) {
    font-size: 1.25rem;
    font-weight: bold;
    margin-bottom: .5rem;
    margin-top: 1rem;
    line-height: normal;
  }
  
  :global(.ProseMirror h4) {
    font-size: 1rem;
    font-weight: bold;
    margin-bottom: .5rem;
    margin-top: 1rem;
    line-height: normal;
  }
  
  :global(.ProseMirror hr) {
    margin-bottom: 3em;
    margin-top: 3em;
    border: none;
    border-top: 1px solid #e2e8f0;
  }
  
  /* Heading button styles */
  :global(.heading-button) {
    display: inline-block;
    margin-left: 8px;
    color: #666;
    cursor: pointer;
    font-size: 0.8em;
    user-select: none;
    transition: color 0.2s;
  }
  
  :global(.heading-button:hover) {
    color: #333;
  }
  
  /* Print styles - hide collapse buttons */
  @media print {
    :global(.heading-button) {
      display: none !important;
    }
  }
  
  /* Folded content styles */
  :global(.folded-content) {
    display: none !important;
  }
  
  /* LaTeX styles */
  :global([data-type="inline-math"]) {
    display: inline-flex;
    align-items: center;
    cursor: pointer;
    padding: 0 2px;
    border-radius: 2px;
  }
  
  :global([data-type="inline-math"]:hover) {
    background-color: rgba(0, 0, 0, 0.05);
  }
  
  :global([data-type="block-math"]) {
    display: flex;
    justify-content: center;
    margin: 1rem 0;
    cursor: pointer;
    border-radius: 4px;
  }
  
  :global([data-type="block-math"]:hover) {
    background-color: rgba(0, 0, 0, 0.05);
  }
  
  :global(.math-block) {
    display: flex;
    justify-content: center;
    width: 100%;
  }
  
  :global(.katex) {
    font-size: 1.1em;
  }
  
  /* Table styles */
  :global(.ProseMirror table) {
    border-collapse: collapse;
    width: 100%;
    font-size: .875em;
    margin-bottom: .25rem;
    margin-top: .25rem;
  }
  
  :global(.ProseMirror th) {
    background-color: #f0f0f0;
    padding: 0.5rem;
    border: 1px solid #ddd;
  }
  
  :global(.ProseMirror th p) {
    margin-bottom: 0;
  }
  
  :global(.ProseMirror td) {
    padding: 0.5rem;
    border: 1px solid #ddd;
  }
  
  :global(.ProseMirror td p) {
    margin-bottom: 0;
  }
  
  /* List styles */
  :global(.ProseMirror ul) {
    list-style-type: disc;
    padding-left: 1.625em;
    margin-bottom: 1.25em;
  }
  
  :global(.ProseMirror ol) {
    list-style-type: decimal;
    padding-left: 1.625em;
    margin-bottom: 1.25em;
  }
  
  :global(.ProseMirror li) {
    margin-bottom: 0.5rem;
    margin-top: .5em;
    padding-left: .375em;
  }
  
  :global(.ProseMirror li p) {
    margin: 0;
  }
  
  /* Blockquote styles */
  :global(.ProseMirror blockquote) {
    border-left: 3px solid #e2e8f0;
    padding-left: 1rem;
    margin-left: 0;
    margin-right: 0;
    margin-top: 1rem;
    margin-bottom: 1rem;
    color: #4a5568;
    font-style: italic;
  }
</style>
