import { writable } from 'svelte/store';

type ToastType = 'info' | 'success' | 'warning' | 'error';

interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration: number;
  showSpinner: boolean;
}

function createToastStore() {
  const { subscribe, update } = writable<Toast[]>([]);

  function addToast(
    message: string, 
    type: ToastType = 'info', 
    duration: number = 3000,
    showSpinner: boolean = false
  ): string {
    const id = Date.now().toString();
    
    update(toasts => [
      ...toasts,
      { id, message, type, duration, showSpinner }
    ]);
    
    return id;
  }

  function removeToast(id: string) {
    update(toasts => toasts.filter(toast => toast.id !== id));
  }

  function showSavingToast(filename: string): string {
    return addToast(
      `Saving changes to ${filename} before switching...`, 
      'info', 
      0, // No auto-dismiss
      true // Show spinner
    );
  }

  function hideSavingToast(id: string) {
    removeToast(id);
  }
  
  function showLoadingToast(filename: string): string {
    return addToast(
      `Loading ${filename}...`, 
      'info', 
      0, // No auto-dismiss
      true // Show spinner
    );
  }

  function hideLoadingToast(id: string) {
    removeToast(id);
  }
  
  function showErrorToast(title: string, message: string): string {
    return addToast(
      `${title}: ${message}`, 
      'error', 
      5000, // 5 seconds
      false // No spinner
    );
  }

  return {
    subscribe,
    addToast,
    removeToast,
    showSavingToast,
    hideSavingToast,
    showLoadingToast,
    hideLoadingToast,
    showErrorToast
  };
}

export const toastStore = createToastStore();
