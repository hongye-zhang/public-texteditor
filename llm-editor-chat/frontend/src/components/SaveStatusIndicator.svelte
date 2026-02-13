<!-- Save Status Indicator Component -->
<script lang="ts">
  import { derived } from 'svelte/store';
  import { activeFile } from '../features/file-management/stores/fileStore';
  
  // Derived store for save status
  const saveStatus = derived(activeFile, ($activeFile) => {
    if (!$activeFile) return { text: '', icon: '', class: '' };
    
    // File is currently being saved to Google Drive
    if ($activeFile.isSaving) {
      return {
        text: 'Saving to Drive...',
        icon: 'fa-cloud-arrow-up',
        class: 'saving'
      };
    }
    
    // File has been saved locally but not yet to Google Drive
    if ($activeFile.isSavedLocally && $activeFile.isDirty) {
      const timeAgo = $activeFile.lastLocalSave ? getTimeAgo($activeFile.lastLocalSave) : '';
      return {
        text: `Saved locally ${timeAgo}`,
        icon: 'fa-floppy-disk',
        class: 'saved-locally'
      };
    }
    
    // File is fully saved (both locally and to Google Drive)
    if (!$activeFile.isDirty) {
      const timeAgo = $activeFile.lastCloudSave ? getTimeAgo($activeFile.lastCloudSave) : '';
      return {
        text: `All changes saved ${timeAgo}`,
        icon: 'fa-cloud-check',
        class: 'saved'
      };
    }
    
    // Default case - file has unsaved changes
    return {
      text: 'Unsaved changes',
      icon: 'fa-circle',
      class: 'unsaved'
    };
  });
  
  // Helper function to format time ago
  function getTimeAgo(timestamp: number): string {
    if (!timestamp) return '';
    
    const now = Date.now();
    const seconds = Math.floor((now - timestamp) / 1000);
    
    if (seconds < 5) return 'just now';
    if (seconds < 60) return `${seconds}s ago`;
    
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    
    return '';
  }
</script>

<div class="save-status-dot {$saveStatus.class}" title="{$saveStatus.text}"></div>

<style>
  .save-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    margin: 0 8px;
    transition: background-color 0.3s ease;
  }
  
  .saving {
    background-color: #3498db; /* 蓝色 - 保存中 */
    animation: pulse 1.5s infinite;
  }
  
  .saved-locally {
    background-color: #f39c12; /* 橙色 - 本地已保存 */
  }
  
  .saved {
    background-color: #2ecc71; /* 绿色 - 完全保存 */
  }
  
  .unsaved {
    background-color: #e74c3c; /* 红色 - 未保存 */
  }
  
  @keyframes pulse {
    0% { opacity: 0.6; }
    50% { opacity: 1; }
    100% { opacity: 0.6; }
  }
</style>
