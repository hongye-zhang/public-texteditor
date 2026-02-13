import { writable } from 'svelte/store';
import { locale } from '$lib/i18n';
import { getLanguageName } from '$lib/i18n/languageUtils';

// Base system prompt without language instructions
const BASE_SYSTEM_PROMPT = "You are a helpful assistant for a text editor application. Help the user with their writing, editing, and formatting needs.";

// Create a writable store for the system prompt
export const systemPrompt = writable<string>(BASE_SYSTEM_PROMPT);

// Initialize the system prompt with the current language
let currentLocale: string;

// Subscribe to locale changes and update the system prompt
locale.subscribe((newLocale) => {
  currentLocale = newLocale;
  updateSystemPrompt();
});

/**
 * Updates the system prompt with language-specific instructions
 */
function updateSystemPrompt() {
  const languageName = getLanguageName(currentLocale);
  const updatedPrompt = `${BASE_SYSTEM_PROMPT} Please respond in ${languageName}.`;
  systemPrompt.set(updatedPrompt);
}

/**
 * Gets the current system prompt
 * @returns The current system prompt with language instructions
 */
export function getCurrentSystemPrompt(): string {
  return `${BASE_SYSTEM_PROMPT} Please respond in ${getLanguageName(currentLocale)}.`;
}

/**
 * Gets a custom system prompt with additional instructions
 * @param additionalInstructions - Additional instructions to add to the system prompt
 * @returns A custom system prompt with language instructions
 */
export function getCustomSystemPrompt(additionalInstructions: string): string {
  return `${BASE_SYSTEM_PROMPT} ${additionalInstructions} Please respond in ${getLanguageName(currentLocale)}.`;
}
