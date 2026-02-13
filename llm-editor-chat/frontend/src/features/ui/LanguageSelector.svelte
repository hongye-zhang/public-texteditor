<script lang="ts">
  import { locale, locales, setLocale } from '$lib/i18n';
  import { t } from '$lib/i18n';
  import './settings.css';
  
  // Create an array of available languages from the locales object
  const availableLanguages = Object.keys(locales).map(code => ({
    code,
    name: locales[code]
  }));
  
  function handleChange(event: Event) {
    const target = event.target as HTMLSelectElement;
    setLocale(target.value);
  }
</script>

<div class="language-selector">
  <div class="language-selector-label">
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="settings-section-icon">
      <circle cx="12" cy="12" r="10"></circle>
      <line x1="2" y1="12" x2="22" y2="12"></line>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
    </svg>
  </div>
  <select bind:value={$locale} on:change={handleChange} aria-label={$t('settings.language')} title={$t('settings.language')}>
    {#each availableLanguages as language}
      <option value={language.code}>{language.name}</option>
    {/each}
  </select>
</div>

<style>
  .language-selector {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
  }
  
  .language-selector-label {
    display: flex;
    align-items: center;
  }
  
  select {
    padding: 0.5rem;
    border-radius: 0.25rem;
    border: 1px solid #ccc;
    background-color: white;
    cursor: pointer;
    flex-grow: 1;
    min-width: 150px;
  }
  
  select:focus {
    outline: none;
    border-color: #4f46e5;
    box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
  }
  
  /* Dark mode support */
  :global(body.dark-theme) select {
    background-color: #1f2937;
    border-color: #4b5563;
    color: #f3f4f6;
  }
  
  :global(body.dark-theme) select:focus {
    border-color: #818cf8;
    box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.2);
  }
</style>
