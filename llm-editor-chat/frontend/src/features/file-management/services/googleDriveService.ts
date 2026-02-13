import { googleAuthStore, isAuthenticated } from '../../auth/stores/googleAuthStore';
import { get } from 'svelte/store';

// Constants
const APP_FOLDER_NAME = 'LLM Editor Chat';
const FILE_MIME_TYPE = 'application/json';

// Interface for Google Drive file metadata
export interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  createdTime: string;
  modifiedTime: string;
  content?: string;
}

// Cache for the app folder ID
let appFolderId: string | null = null;

/**
 * Get or create the application folder in Google Drive
 * @throws Error if not authenticated or if folder creation fails
 */
export async function getAppFolder(): Promise<string> {
  // Return cached folder ID if available
  if (appFolderId) {
    return appFolderId;
  }

  // Check authentication
  if (!get(isAuthenticated)) {
    throw new Error('Not authenticated with Google Drive');
  }

  try {
    // Search for existing folder
    try {
      const response = await window.gapi.client.drive.files.list({
        q: `name='${APP_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false`,
        spaces: 'drive',
        fields: 'files(id, name)'
      });
      
      // If folder exists, return it
      if (response?.result?.files && response.result.files.length > 0) {
        const folderId = response.result.files[0]?.id;
        if (folderId) {
          console.log(`Found existing app folder "${APP_FOLDER_NAME}" with ID: ${folderId}`);
          appFolderId = folderId;
          return folderId;
        }
      } else {
        console.log(`App folder "${APP_FOLDER_NAME}" not found, will create it`);
      }
    } catch (error: any) {
      // Handle authentication errors
      if (error?.status === 401 || error?.status === 403 || 
          (error?.result?.error?.code === 401) || (error?.result?.error?.code === 403)) {
        await googleAuthStore.handleAuthError(error);
      }
      throw error;
    }

    // Create folder if it doesn't exist
    const folderMetadata = {
      name: APP_FOLDER_NAME,
      mimeType: 'application/vnd.google-apps.folder'
    };

    try {
      const folder = await window.gapi.client.drive.files.create({
        resource: folderMetadata,
        fields: 'id'
      });

      if (folder?.result?.id) {
        appFolderId = folder.result.id;
        return folder.result.id;
      } else {
        throw new Error('Failed to create folder: No ID returned');
      }
    } catch (folderError: any) {
      // Handle authentication errors
      if (folderError?.status === 401 || folderError?.status === 403 || 
          (folderError?.result?.error?.code === 401) || (folderError?.result?.error?.code === 403)) {
        await googleAuthStore.handleAuthError(folderError);
      }
      console.error('Error creating app folder:', folderError);
      throw new Error('Failed to create app folder in Google Drive');
    }
  } catch (error) {
    console.error('Error getting/creating app folder:', error);
    throw error;
  }
}

/**
 * List all files in the app folder
 * @returns Array of DriveFile objects, empty array if not authenticated
 */
export async function listFiles(): Promise<DriveFile[]> {
  // Check authentication
  if (!get(isAuthenticated)) {
    return [];
  }

  try {
    const folderId = await getAppFolder();

    try {
      const query = `'${folderId}' in parents and trashed=false`;
      console.log(`Listing files with query: ${query}`);
      
      const response = await window.gapi.client.drive.files.list({
        q: query,
        spaces: 'drive',
        fields: 'files(id, name, mimeType, createdTime, modifiedTime)',
        orderBy: 'modifiedTime desc'
      });

      return response?.result?.files || [];
    } catch (apiError: any) {
      // Handle authentication errors
      if (apiError?.status === 401 || apiError?.status === 403 || 
          (apiError?.result?.error?.code === 401) || (apiError?.result?.error?.code === 403)) {
        await googleAuthStore.handleAuthError(apiError);
      }
      throw apiError;
    }
  } catch (error) {
    console.error('Error listing files:', error);
    return [];
  }
}

/**
 * Get file content by ID
 */
export async function getFileContent(fileId: string): Promise<string> {
  // No retries - we'll handle auth errors through the central handler
  
  // Check authentication
  if (!get(isAuthenticated)) {
    throw new Error('Not authenticated with Google Drive');
  }

  try {
    // Get file metadata to confirm it's the right type
    let metadata;
    try {
      metadata = await window.gapi.client.drive.files.get({
        fileId: fileId,
        fields: 'id, name, mimeType'
      });
    } catch (apiError: any) {
      // Handle authentication errors
      if (apiError?.status === 401 || apiError?.status === 403 || 
          (apiError?.result?.error?.code === 401) || (apiError?.result?.error?.code === 403)) {
        await googleAuthStore.handleAuthError(apiError);
      }
      throw apiError;
    }

    // Get and potentially refresh the authentication token
    const token = await googleAuthStore.getToken();
    if (!token) {
      throw new Error('No authentication token available');
    }

    // Download the file content
    const response = await fetch(
      `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    );

    // Handle unauthorized errors specifically
    if (response.status === 401 || response.status === 403) {
      console.log(`Received ${response.status} error, handling auth error...`);
      // Use our centralized auth error handler
      await googleAuthStore.handleAuthError({ status: response.status });
      // Don't retry automatically - let the user sign in again
      throw new Error(`Authentication error: ${response.statusText}`);
    }
    
    if (!response.ok) {
      throw new Error(`Failed to fetch file content: ${response.statusText}`);
    }

    const rawContent = await response.text();
    
    // Check if content is empty
    if (!rawContent || rawContent.trim() === '') {
      throw new Error('File content is empty');
    }
    
    try {
      // Try to parse as JSON
      const parsedContent = JSON.parse(rawContent);
      
      // Return the parsed content as a string
      if (typeof parsedContent === 'string') {
        // Content was already a JSON string, return it
        console.log(`File ${fileId} loaded: JSON string format`);
        return parsedContent;
      } else {
        // Content was a JSON object, which is unexpected
        console.error('Invalid content format: expected string content', parsedContent);
        throw new Error('Invalid content format: expected string content');
      }
    } catch (parseError) {
      // For backward compatibility with old files
      console.warn(`File ${fileId} is not in JSON format, converting to JSON for next save:`, parseError);
      
      // If it's not valid JSON, it might be HTML or plain text from old format
      // Check if it looks like HTML content
      if (rawContent.trim().startsWith('<') && rawContent.includes('</')) {
        console.log(`File ${fileId} appears to be raw HTML, will be saved as JSON on next save`);
      } else {
        console.log(`File ${fileId} has unknown format, will be saved as JSON on next save`);
      }
      
      // Return it as is for backward compatibility
      return rawContent;
    }
  } catch (error) {
    console.error('Error getting file content:', error);
    throw error;
  }
}

/**
 * Create a new file in Google Drive
 */
export async function createFile(title: string, content: string = ''): Promise<DriveFile> {
  // Check authentication
  if (!get(isAuthenticated)) {
    throw new Error('Not authenticated with Google Drive');
  }

  try {
    const folderId = await getAppFolder();
    
    // Create file metadata
    const fileName = title.endsWith('.json') ? title : `${title}.json`;
    const fileMetadata = {
      name: fileName,
      mimeType: FILE_MIME_TYPE,
      parents: [folderId]
    };

    // Create an empty file first
    const file = await window.gapi.client.drive.files.create({
      resource: fileMetadata,
      fields: 'id, name, mimeType, createdTime, modifiedTime'
    });

    if (!file?.result?.id) {
      throw new Error('Failed to create file: No ID returned');
    }

    // If content was provided, update the file with content
    if (content) {
      await updateFileContent(file.result.id, content);
    }

    return {
      id: file.result.id,
      name: file.result.name || fileName,
      mimeType: file.result.mimeType || FILE_MIME_TYPE,
      createdTime: file.result.createdTime || new Date().toISOString(),
      modifiedTime: file.result.modifiedTime || new Date().toISOString(),
      content
    };
  } catch (error) {
    console.error('Error creating file:', error);
    throw error;
  }
}

/**
 * Update file content
 */
export async function updateFileContent(fileId: string, content: string): Promise<void> {
  // No retries - we'll handle auth errors through the central handler
  
  // Check authentication
  if (!get(isAuthenticated)) {
    throw new Error('Not authenticated with Google Drive');
  }

  try {
    // Get and potentially refresh the authentication token
    const token = await googleAuthStore.getToken();
    if (!token) {
      throw new Error('No authentication token available');
    }
    
    // Validate content is not empty
    if (!content || content.trim() === '') {
      throw new Error('Cannot save empty content');
    }
    
    // Ensure content is a string before JSON.stringify
    if (typeof content !== 'string') {
      console.error('Content must be a string for JSON.stringify');
      throw new Error('Content must be a string for JSON.stringify');
    }
    
    // Convert content to JSON string format
    // We JSON.stringify the string to ensure it's a valid JSON value
    const jsonContent = JSON.stringify(content);
    
    // Verify the JSON content is properly formatted
    try {
      // This should parse back to the original string
      const verifiedContent = JSON.parse(jsonContent);
      if (verifiedContent !== content) {
        console.warn('JSON verification failed - content changed during stringify/parse cycle');
      } else {
        console.log(`File ${fileId} saved in proper JSON format, length: ${jsonContent.length}`);
      }
    } catch (error) {
      console.error('Failed to verify JSON content:', error);
      throw new Error('Failed to create valid JSON content');
    }

    // Use the upload API to update file content
    const response = await fetch(
      `https://www.googleapis.com/upload/drive/v3/files/${fileId}?uploadType=media`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': FILE_MIME_TYPE,
          Authorization: `Bearer ${token}`
        },
        body: jsonContent
      }
    );

    // Handle unauthorized errors specifically
    if (response.status === 401 || response.status === 403) {
      console.log(`Received ${response.status} error, handling auth error...`);
      // Use our centralized auth error handler
      await googleAuthStore.handleAuthError({ status: response.status });
      // Don't retry automatically - let the user sign in again
      throw new Error(`Authentication error: ${response.statusText}`);
    }
    
    if (!response.ok) {
      throw new Error(`Failed to update file: ${response.statusText}`);
    }
  } catch (error) {
    console.error('Error updating file content:', error);
    throw error;
  }
}

/**
 * Delete a file
 */
export async function deleteFile(fileId: string): Promise<void> {
  // Check authentication
  if (!get(isAuthenticated)) {
    throw new Error('Not authenticated with Google Drive');
  }

  try {
    try {
      await window.gapi.client.drive.files.delete({
        fileId: fileId
      });
    } catch (apiError: any) {
      // Handle authentication errors
      if (apiError?.status === 401 || apiError?.status === 403 || 
          (apiError?.result?.error?.code === 401) || (apiError?.result?.error?.code === 403)) {
        await googleAuthStore.handleAuthError(apiError);
      }
      throw apiError;
    }
  } catch (error) {
    console.error('Error deleting file:', error);
    throw error;
  }
}

/**
 * Update file metadata (e.g., rename)
 */
export async function updateFileMetadata(fileId: string, metadata: { name?: string }): Promise<DriveFile> {
  // Check authentication
  if (!get(isAuthenticated)) {
    throw new Error('Not authenticated with Google Drive');
  }

  try {
    let response;
    try {
      response = await window.gapi.client.drive.files.update({
        fileId: fileId,
        resource: metadata,
        fields: 'id, name, mimeType, createdTime, modifiedTime'
      });
    } catch (apiError: any) {
      // Handle authentication errors
      if (apiError?.status === 401 || apiError?.status === 403 || 
          (apiError?.result?.error?.code === 401) || (apiError?.result?.error?.code === 403)) {
        await googleAuthStore.handleAuthError(apiError);
      }
      throw apiError;
    }

    if (!response?.result?.id) {
      throw new Error('Failed to update file metadata: No ID returned');
    }

    return {
      id: response.result.id,
      name: response.result.name || '',
      mimeType: response.result.mimeType || FILE_MIME_TYPE,
      createdTime: response.result.createdTime || new Date().toISOString(),
      modifiedTime: response.result.modifiedTime || new Date().toISOString()
    };
  } catch (error) {
    console.error('Error updating file metadata:', error);
    throw error;
  }
}
