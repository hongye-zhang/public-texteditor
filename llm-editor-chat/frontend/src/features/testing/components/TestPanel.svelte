<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { getHelloWorld } from '$lib/api';
  
  const dispatch = createEventDispatcher();

  async function handleTestClick() {
    try {
      const response = await getHelloWorld();
      dispatch('test', {
        type: 'sample',
        action: 'insert-text',
        content: response.content
      });
    } catch (error) {
      console.error('Failed to get hello world example:', error);
      alert('Failed to fetch example text');
    }
  }
</script>

<div class="test-panel bg-gray-100 p-4 rounded-lg">
  <h2 class="text-lg font-semibold mb-4">Test Functions</h2>
  <div class="flex flex-col gap-2">
    <button
      class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md transition-colors"
      on:click={handleTestClick}
    >
      <i class="fas fa-magic mr-2"></i>
      Insert Hello World
    </button>
  </div>
</div>

<style>
  .test-panel {
    height: 100%;
    min-width: 200px;
  }
</style>
