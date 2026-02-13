/**
 * Template Store
 * 
 * This store manages template state and provides methods for interacting with the template API.
 * It handles loading, caching, searching, and creating templates.
 */
import { writable, derived, get } from 'svelte/store';
import * as templateApi from '../lib/api/templateApi';

// Check if we're running in Electron
const isElectron = typeof window !== 'undefined' && window.environment && window.environment.isElectron;

/**
 * @typedef {Object} Template
 * @property {string} id - Template ID
 * @property {string} name - Template name
 * @property {string} prompt - Template prompt
 * @property {string[]} [category] - Template categories
 * @property {string[]} [required_fields] - Required fields
 * @property {string} [visibility] - Template visibility (public, private, team)
 * @property {Object} [metadata] - Additional metadata
 * @property {number} [usage_count] - Usage count
 * @property {number} [avg_rating] - Average rating
 * @property {string} [created_at] - Creation timestamp
 * @property {string} [updated_at] - Last update timestamp
 */

/**
 * @typedef {Object} NewTemplate
 * @property {string} name - Template name
 * @property {string} prompt - Template prompt
 * @property {string[]} [category] - Template categories
 * @property {string[]} [required_fields] - Required fields
 * @property {string} [visibility] - Template visibility (public, private, team)
 * @property {Object} [metadata] - Additional metadata
 */

/**
 * @typedef {Object} TemplateState
 * @property {Template[]} templates - All templates
 * @property {Template[]} userTemplates - User's templates
 * @property {string[]} categories - Available categories
 * @property {string|null} selectedCategory - Selected category
 * @property {string} searchTerm - Search term
 * @property {boolean} isLoading - Loading state
 * @property {string|null} error - Error message
 * @property {number} currentPage - Current page number
 * @property {boolean} hasMoreTemplates - Whether there are more templates to load
 * @property {boolean} isOffline - Whether the app is in offline mode
 */

/**
 * @typedef {Object} TemplateRating
 * @property {number} rating - Rating value (1-5)
 * @property {string} [feedback] - Optional feedback
 */

/**
 * @typedef {Object} TemplateStore
 * @property {function} subscribe
 * @property {function():Promise<void>} init
 * @property {function(Object):Promise<void>} loadTemplates
 * @property {function(string|null):void} setCategory
 * @property {function(string):void} searchTemplates
 * @property {function(NewTemplate):Promise<Template>} createTemplate
 * @property {function(string,NewTemplate):Promise<Template>} updateTemplate
 * @property {function(string):Promise<void>} deleteTemplate
 * @property {function(string):Promise<void>} useTemplate
 * @property {function(string,number,string):Promise<void>} rateTemplate
 * @property {function():void} clearError
 * @property {function():void} reset
 */

// Initial state
/** @type {TemplateState} */
const initialState = {
  templates: [],
  userTemplates: [],
  categories: [],
  selectedCategory: null,
  searchTerm: '',
  isLoading: false,
  error: null,
  currentPage: 0,
  hasMoreTemplates: true,
  isOffline: false
};

// Blank template that's always available
/** @type {Template} */
const blankTemplate = {
  id: 'blank',
  name: 'Blank Document',
  prompt: '',
  category: ['General'],
  visibility: 'public',
  usage_count: 0,
  created_at: new Date().toISOString()
};

// Create the writable store
/**
 * Create a template store
 * 
 * @returns {import('svelte/store').Readable<TemplateState> & TemplateStore} Template store
 */
function createTemplateStore() {
  const { subscribe, set, update } = writable(initialState);

  return {
    subscribe,
    
    /**
     * Initialize the store and load templates
     */
    init: async () => {
      // We need to call loadTemplates directly instead of through get()
      // since the store is still being created
      return templateStore.loadTemplates({});
    },
    
    
    /**
     * Load templates with optional filtering
     * 
     * @param {Object} options - Load options
     * @param {string} [options.search] - Optional search term
     * @param {string} [options.category] - Optional category filter
     * @param {boolean} [options.reset=false] - Whether to reset pagination
     */
    loadTemplates: async (options = {}) => {
      update(state => ({ ...state, isLoading: true, error: null }));
      
      const {
        search = '',
        category = null,
        reset = false
      } = options;
      
      const limit = 20;
      const page = reset ? 0 : get(templateStore).currentPage;
      
      try {
        /** @type {Template[]} */
        let publicTemplates = [];
        /** @type {Template[]} */
        let userTemplates = [];
        let isOffline = false;
        
        try {
          // Load public templates
          publicTemplates = /** @type {Template[]} */ (await templateApi.getTemplates({
            search,
            category,
            limit,
            offset: page * limit,
            visibility: 'public'
          }));
          
          // Load user templates if not searching public templates
          if (!options.search && !options.category) {
            if (isElectron && typeof window !== 'undefined' && window.electronAPI && window.electronAPI.fileSystem && typeof window.electronAPI.fileSystem.listTemplateFiles === 'function') {
              // In Electron, load private templates from filesystem
              try {
                userTemplates = await window.electronAPI.fileSystem.listTemplateFiles();
                console.log('Loaded private templates from filesystem:', userTemplates.length);
              } catch (fsError) {
                console.error('Error loading templates from filesystem:', fsError);
                // Fallback to API if filesystem access fails
                userTemplates = /** @type {Template[]} */ (await templateApi.getTemplates({
                  visibility: 'private',
                  limit: 100,
                  offset: 0
                }));
              }
            } else {
              // In browser, load from API
              userTemplates = /** @type {Template[]} */ (await templateApi.getTemplates({
                visibility: 'private',
                limit: 100,
                offset: 0
              }));
            }
          }
        } catch (fetchError) {
          // Check if this is a network error (Failed to fetch)
          const isNetworkError = fetchError instanceof TypeError && 
            (fetchError.message.includes('Failed to fetch') ||
             fetchError.message.includes('NetworkError') ||
             fetchError.message.includes('Network request failed'));
          
          if (isNetworkError) {
            console.log('User appears to be offline. Using cached templates.');
          } else {
            console.error('Error loading templates:', fetchError);
          }
          
          isOffline = true;
          
          // Try to load cached templates
          if (isElectron && typeof window !== 'undefined' && window.electronAPI && window.electronAPI.fileSystem && typeof window.electronAPI.fileSystem.listTemplateFiles === 'function') {
            // In Electron, try to load from filesystem
            try {
              userTemplates = await window.electronAPI.fileSystem.listTemplateFiles();
              console.log('Loaded private templates from filesystem while offline:', userTemplates.length);
            } catch (fsError) {
              console.error('Error loading templates from filesystem while offline:', fsError);
              // Fallback to localStorage
              try {
                const cachedUserTemplatesJson = localStorage.getItem('cached_user_templates');
                if (cachedUserTemplatesJson) {
                  userTemplates = /** @type {Template[]} */ (JSON.parse(cachedUserTemplatesJson));
                }
              } catch (cacheError) {
                console.error('Error loading cached user templates from localStorage:', cacheError);
              }
            }
          } else {
            // In browser, load from localStorage
            try {
              const cachedTemplatesJson = localStorage.getItem('cached_templates');
              const cachedUserTemplatesJson = localStorage.getItem('cached_user_templates');
              
              if (cachedTemplatesJson) {
                publicTemplates = /** @type {Template[]} */ (JSON.parse(cachedTemplatesJson));
              }
              
              if (cachedUserTemplatesJson) {
                userTemplates = /** @type {Template[]} */ (JSON.parse(cachedUserTemplatesJson));
              }
            } catch (cacheError) {
              console.error('Error loading cached templates:', cacheError);
            }
          }
          
          // Always include the blank template when offline
          if (!publicTemplates.some((t) => t.id === blankTemplate.id)) {
            publicTemplates = [blankTemplate, ...publicTemplates];
          }
        }
        
        // Cache public templates in localStorage for offline use
        if (!isOffline && publicTemplates.length > 0) {
          try {
            localStorage.setItem('cached_templates', JSON.stringify(publicTemplates));
            
            // Only cache user templates in localStorage if not using Electron
            if (!isElectron && userTemplates.length > 0) {
              localStorage.setItem('cached_user_templates', JSON.stringify(userTemplates));
            }
          } catch (cacheError) {
            console.error('Error caching templates:', cacheError);
          }
        }
        
        // Extract unique categories from all templates
        const allTemplates = [...publicTemplates, ...userTemplates];
        const categories = [...new Set(
          allTemplates.flatMap(template => template.category || [])
        )].sort();
        
        update(state => ({
          ...state,
          templates: options.reset ? publicTemplates : [...state.templates, ...publicTemplates],
          userTemplates,
          categories,
          currentPage: page + 1,
          hasMoreTemplates: publicTemplates.length === limit && !isOffline,
          isLoading: false,
          isOffline,
          error: isOffline ? 'You appear to be offline. Showing available templates.' : null
        }));
      } catch (error) {
        console.error('Error loading templates:', error);
        
        // Try to load the blank template and any cached templates as a fallback
        /** @type {Template[]} */
        let cachedTemplates = [];
        try {
          const cachedTemplatesJson = localStorage.getItem('cached_templates');
          if (cachedTemplatesJson) {
            cachedTemplates = /** @type {Template[]} */ (JSON.parse(cachedTemplatesJson));
          }
        } catch (cacheError) {
          console.error('Error loading cached templates:', cacheError);
        }
        
        // Always include the blank template
        if (!cachedTemplates.some((t) => t.id === blankTemplate.id)) {
          cachedTemplates = [blankTemplate, ...cachedTemplates];
        }
        
        update(state => ({ 
          ...state, 
          templates: cachedTemplates,
          isLoading: false, 
          isOffline: true,
          error: 'Failed to load templates. Showing cached templates.' 
        }));
      }
    },
    
    
    /**
     * Set the selected category
     * 
     * @param {string|null} category - Category to select or null to clear
     */
    setCategory: (category) => {
      update(state => ({ ...state, selectedCategory: category }));
      // Call loadTemplates directly on the templateStore object
      templateStore.loadTemplates({ category, reset: true });
    },
    
    /**
     * Search templates by term
     * 
     * @param {string} searchTerm - Search term
     */
    searchTemplates: (searchTerm) => {
      update(state => ({ ...state, searchTerm }));
      // Call loadTemplates directly on the templateStore object
      templateStore.loadTemplates({ search: searchTerm, reset: true });
    },
    
    /**
     * Create a new template
     * 
     * @param {NewTemplate} template - Template data
     * @returns {Promise<Template>} Created template
     */
    createTemplate: async (template) => {
      update(state => ({ ...state, isLoading: true, error: null }));
      
      try {
        /** @type {Template} */
        let createdTemplate;
        
        // Handle private templates locally
        if (template.visibility === 'private') {
          console.log('Creating private template locally:', template.name);
          
          // Generate a unique ID for the local template
          const localId = `local_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
          
          // Create the template object
          createdTemplate = {
            ...template,
            id: localId,
            usage_count: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          };
          
          if (isElectron && typeof window !== 'undefined' && window.electronAPI && window.electronAPI.fileSystem && typeof window.electronAPI.fileSystem.saveTemplateFile === 'function') {
            // In Electron, save to filesystem
            try {
              await window.electronAPI.fileSystem.saveTemplateFile(localId, createdTemplate);
              console.log('Private template saved to filesystem:', createdTemplate.name);
            } catch (fsError) {
              console.error('Error saving template to filesystem:', fsError);
              throw new Error('Failed to save template locally. Please try again.');
            }
          } else {
            // In browser, save to localStorage
            // Get existing cached user templates
            let cachedUserTemplates = [];
            try {
              const cachedUserTemplatesJson = localStorage.getItem('cached_user_templates');
              if (cachedUserTemplatesJson) {
                cachedUserTemplates = JSON.parse(cachedUserTemplatesJson);
              }
            } catch (cacheError) {
              console.error('Error loading cached user templates:', cacheError);
            }
            
            // Add new template to cached user templates
            cachedUserTemplates = [...cachedUserTemplates, createdTemplate];
            
            // Save updated cached user templates
            try {
              localStorage.setItem('cached_user_templates', JSON.stringify(cachedUserTemplates));
              console.log('Private template saved to localStorage:', createdTemplate.name);
            } catch (cacheError) {
              console.error('Error saving template to localStorage:', cacheError);
              throw new Error('Failed to save template locally. Please try again.');
            }
          }
        } else {
          // For public templates, use the API
          createdTemplate = /** @type {Template} */ (await templateApi.createTemplate(template));
        }
        
        update(state => {
          // Update user templates with the new template
          /** @type {Template[]} */
          const userTemplates = [...state.userTemplates, createdTemplate];
          
          // Update categories
          const newCategories = [...new Set([
            ...state.categories,
            ...(createdTemplate.category || [])
          ])].sort();
          
          return {
            ...state,
            userTemplates,
            categories: newCategories,
            isLoading: false
          };
        });
        
        return createdTemplate;
      } catch (error) {
        console.error('Error creating template:', error);
        update(state => ({ 
          ...state, 
          error: 'Failed to create template. Please try again.',
          isLoading: false 
        }));
        throw error;
      }
    },
    
    /**
     * Update an existing template
     * 
     * @param {string} templateId - Template ID
     * @param {Object} updates - Template updates
     * @returns {Promise<Template>} Updated template
     */
    updateTemplate: async (templateId, updates) => {
      update(state => ({ ...state, isLoading: true, error: null }));
      
      try {
        // Check if this is a local template
        const isLocalTemplate = templateId.startsWith('local_');
        
        /** @type {Template} */
        let updatedTemplate;
        
        if (isLocalTemplate) {
          if (isElectron && typeof window !== 'undefined' && window.electronAPI && window.electronAPI.fileSystem && 
              typeof window.electronAPI.fileSystem.readTemplateFile === 'function' && 
              typeof window.electronAPI.fileSystem.saveTemplateFile === 'function') {
            // In Electron, update in filesystem
            try {
              // First read the existing template
              const existingTemplate = await window.electronAPI.fileSystem.readTemplateFile(templateId);
              
              // Update the template
              updatedTemplate = {
                ...existingTemplate,
                ...updates,
                updated_at: new Date().toISOString()
              };
              
              // Save back to filesystem
              await window.electronAPI.fileSystem.saveTemplateFile(templateId, updatedTemplate);
              console.log('Private template updated in filesystem:', updatedTemplate.name);
            } catch (fsError) {
              console.error('Error updating template in filesystem:', fsError);
              throw new Error('Failed to update template. Please try again.');
            }
          } else {
            // For local templates, update in localStorage
            try {
              const cachedUserTemplatesJson = localStorage.getItem('cached_user_templates');
              if (cachedUserTemplatesJson) {
                const cachedUserTemplates = JSON.parse(cachedUserTemplatesJson);
                const templateIndex = cachedUserTemplates.findIndex(t => t.id === templateId);
                
                if (templateIndex !== -1) {
                  // Update the template
                  updatedTemplate = {
                    ...cachedUserTemplates[templateIndex],
                    ...updates,
                    updated_at: new Date().toISOString()
                  };
                  
                  // Replace the old template with the updated one
                  cachedUserTemplates[templateIndex] = updatedTemplate;
                  
                  // Save back to localStorage
                  localStorage.setItem('cached_user_templates', JSON.stringify(cachedUserTemplates));
                } else {
                  throw new Error('Template not found');
                }
              } else {
                throw new Error('No cached templates found');
              }
            } catch (cacheError) {
              console.error('Error updating cached template:', cacheError);
              throw new Error('Failed to update template. Please try again.');
            }
          }
        } else {
          // For remote templates, use the API
          updatedTemplate = /** @type {Template} */ (await templateApi.updateTemplate(templateId, updates));
        }
        
        update(state => {
          // Update user templates with the new template
          /** @type {Template[]} */
          const userTemplates = state.userTemplates.map((t) => 
            t.id === updatedTemplate.id ? updatedTemplate : t
          );
          
          // Update categories
          const newCategories = [...new Set([
            ...state.categories,
            ...(updatedTemplate.category || [])
          ])].sort();
          
          return {
            ...state,
            userTemplates,
            categories: newCategories,
            isLoading: false
          };
        });
        
        return updatedTemplate;
      } catch (error) {
        console.error('Error updating template:', error);
        update(state => ({ 
          ...state, 
          error: 'Failed to update template. Please try again.',
          isLoading: false 
        }));
        throw error;
      }
    },
    
    /**
     * Delete a template
     * 
     * @param {string} templateId - Template ID
     * @returns {Promise<void>}
     */
    deleteTemplate: async (templateId) => {
      update(state => ({ ...state, isLoading: true, error: null }));
      
      try {
        // Check if this is a local template
        const isLocalTemplate = templateId.startsWith('local_');
        
        if (isLocalTemplate) {
          if (isElectron && typeof window !== 'undefined' && window.electronAPI && window.electronAPI.fileSystem && typeof window.electronAPI.fileSystem.deleteTemplateFile === 'function') {
            // In Electron, delete from filesystem
            try {
              await window.electronAPI.fileSystem.deleteTemplateFile(templateId);
              console.log('Private template deleted from filesystem:', templateId);
            } catch (fsError) {
              console.error('Error deleting template from filesystem:', fsError);
              throw new Error('Failed to delete template. Please try again.');
            }
          } else {
            // In browser, remove from localStorage
            try {
              const cachedUserTemplatesJson = localStorage.getItem('cached_user_templates');
              if (cachedUserTemplatesJson) {
                const cachedUserTemplates = JSON.parse(cachedUserTemplatesJson);
                const updatedTemplates = cachedUserTemplates.filter(t => t.id !== templateId);
                localStorage.setItem('cached_user_templates', JSON.stringify(updatedTemplates));
              }
            } catch (cacheError) {
              console.error('Error updating cached templates:', cacheError);
              throw new Error('Failed to delete template. Please try again.');
            }
          }
        } else {
          // For remote templates, use the API
          await templateApi.deleteTemplate(templateId);
        }
        
        update(state => {
          // Remove from templates and userTemplates
          const templates = state.templates.filter((t) => t.id !== templateId);
          const userTemplates = state.userTemplates.filter((t) => t.id !== templateId);
          
          // Update categories
          const allTemplates = [...templates, ...userTemplates];
          const categories = [...new Set(
            allTemplates.flatMap(template => template.category || [])
          )].sort();
          
          return {
            ...state,
            templates,
            userTemplates,
            categories,
            isLoading: false
          };
        });
      } catch (error) {
        console.error('Error deleting template:', error);
        update(state => ({ 
          ...state, 
          isLoading: false, 
          error: 'Failed to delete template. Please try again.' 
        }));
        throw error;
      }
    },
    
    /**
     * Use a template and increment its usage count
     * 
     * @param {string} templateId - Template ID
     * @returns {Promise<void>}
     */
    useTemplate: async (templateId) => {
      try {
        await templateApi.useTemplate(templateId);
      } catch (error) {
        console.error('Error using template:', error);
      }
    },
    
    /**
     * Rate a template
     * 
     * @param {string} templateId - Template ID
     * @param {number} rating - Rating (1-5)
     * @param {string} [feedback] - Optional feedback
     * @returns {Promise<void>}
     */
    rateTemplate: async (templateId, rating, feedback) => {
      try {
        /** @type {TemplateRating} */
        const ratingData = { rating, feedback };
        await templateApi.rateTemplate(templateId, ratingData);
      } catch (error) {
        console.error('Error rating template:', error);
      }
    },
    
    /**
     * Clear any error in the store
     */
    clearError: () => {
      update(state => ({ ...state, error: null }));
    },
    
    /**
     * Reset the store to initial state
     */
    reset: () => {
      set(initialState);
    }
  };
}

// Create and export the store
export const templateStore = createTemplateStore();

// Create derived stores for easier consumption
/** @type {import('svelte/store').Readable<Template[]>} */
export const templates = derived({ subscribe: templateStore.subscribe }, $store => $store.templates);
/** @type {import('svelte/store').Readable<Template[]>} */
export const userTemplates = derived({ subscribe: templateStore.subscribe }, $store => $store.userTemplates);
/** @type {import('svelte/store').Readable<string[]>} */
export const categories = derived({ subscribe: templateStore.subscribe }, $store => $store.categories);
/** @type {import('svelte/store').Readable<boolean>} */
export const isLoading = derived({ subscribe: templateStore.subscribe }, $store => $store.isLoading);
/** @type {import('svelte/store').Readable<string|null>} */
export const error = derived({ subscribe: templateStore.subscribe }, $store => $store.error);
