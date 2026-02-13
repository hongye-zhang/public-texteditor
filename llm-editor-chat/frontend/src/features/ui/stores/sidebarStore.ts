import { writable } from 'svelte/store';

// Create stores for sidebar collapsed states with localStorage persistence
function createPersistentStore(key: string, initialValue: boolean) {
  // Initialize from localStorage if available, otherwise use default value
  let initialState = initialValue;
  
  try {
    if (typeof localStorage !== 'undefined') {
      const storedValue = localStorage.getItem(key);
      if (storedValue !== null) {
        initialState = storedValue === 'true';
      }
    }
  } catch (error) {
    console.error(`Error reading from localStorage for key ${key}:`, error);
  }
  
  const store = writable<boolean>(initialState);
  
  // Subscribe to changes and update localStorage
  store.subscribe(value => {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(key, String(value));
      }
    } catch (error) {
      console.error(`Error writing to localStorage for key ${key}:`, error);
    }
  });
  
  return {
    ...store,
    toggle: () => {
      store.update(value => !value);
    }
  };
}

// Create stores for both sidebars
export const fileSidebarCollapsed = createPersistentStore('file-sidebar-collapsed', false);
export const chatPanelCollapsed = createPersistentStore('chat-panel-collapsed', false);
