<script lang="ts">
  import Editor from './components/Editor.svelte';
</script>

<main class="container">
  <Editor />
</main>

<style>
  .container {
    width: 100%;
    height: 100%;
    padding: 1rem;
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
      Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    background: #f5f5f5;
  }
</style>
