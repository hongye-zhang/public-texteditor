<script lang="ts">
  import { onMount } from 'svelte';

  let element: HTMLDivElement;
  let content = '';

  onMount(() => {
    if (element) {
      element.contentEditable = 'true';
    }
  });

  function handleInput(event: Event) {
    const target = event.target as HTMLDivElement;
    content = target.textContent || '';
  }
</script>

<div 
  class="editor" 
  bind:this={element}
  on:input={handleInput}
>
  {#if content}
    {content}
  {:else}
    <p>Start typing...</p>
  {/if}
</div>

<style>
  .editor {
    min-height: 300px;
    background: white;
    border: 1px solid #ddd;
    padding: 1rem;
    outline: none;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .editor p {
    margin: 0;
    color: #666;
  }
</style>
