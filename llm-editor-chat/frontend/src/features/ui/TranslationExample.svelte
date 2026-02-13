<script lang="ts">
  import { t } from '$lib/i18n';
  import LanguageSelector from './LanguageSelector.svelte';
  
  // Example of using variables in translations
  const username = 'User';
  const fileCount = 5;
</script>

<div class="translation-example">
  <div class="language-control">
    <h2>{$t('settings.language')}</h2>
    <LanguageSelector />
  </div>
  
  <div class="example-section">
    <h3>UI Elements</h3>
    <button>{$t('editor.save')}</button>
    <button>{$t('editor.cancel')}</button>
    <button>{$t('editor.delete')}</button>
    
    <div class="placeholder-text">
      {$t('editor.placeholder')}
    </div>
  </div>
  
  <div class="example-section">
    <h3>File Management</h3>
    <ul>
      <li><button>{$t('file.new')}</button></li>
      <li><button>{$t('file.open')}</button></li>
      <li><button>{$t('file.save')}</button></li>
      <li><button>{$t('file.saveAs')}</button></li>
    </ul>
  </div>
</div>

<style>
  .translation-example {
    padding: 1rem;
    max-width: 600px;
    margin: 0 auto;
  }
  
  .language-control {
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  
  .example-section {
    margin-bottom: 2rem;
    padding: 1rem;
    border: 1px solid #eee;
    border-radius: 0.5rem;
  }
  
  button {
    margin-right: 0.5rem;
    margin-bottom: 0.5rem;
    padding: 0.5rem 1rem;
    background-color: #4f46e5;
    color: white;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
  }
  
  button:hover {
    background-color: #4338ca;
  }
  
  .placeholder-text {
    margin-top: 1rem;
    padding: 1rem;
    background-color: #f9fafb;
    border: 1px dashed #d1d5db;
    border-radius: 0.25rem;
    color: #6b7280;
  }
  
  ul {
    list-style-type: none;
    padding: 0;
  }
  
  li {
    margin-bottom: 0.5rem;
  }
</style>
