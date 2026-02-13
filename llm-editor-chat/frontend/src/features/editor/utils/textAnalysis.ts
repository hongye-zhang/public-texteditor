import type { Editor } from '@tiptap/core';

interface TextChunk {
  content: string;
  startPos: number;
  endPos: number;
  type: 'paragraph' | 'heading' | 'list' | 'blockquote';
}

export class TextAnalyzer {
  private editor: Editor;

  constructor(editor: Editor) {
    this.editor = editor;
  }

  // Split document into semantic chunks
  public getDocumentChunks(): TextChunk[] {
    const chunks: TextChunk[] = [];
    const doc = this.editor.state.doc;

    doc.descendants((node, pos) => {
      if (node.isBlock && !node.isText) {
        chunks.push({
          content: node.textContent,
          startPos: pos,
          endPos: pos + node.nodeSize,
          type: this.getNodeType(node.type.name)
        });
      }
    });

    return chunks;
  }

  // Find relevant chunks based on prompt
  public async findRelevantChunks(prompt: string): Promise<TextChunk[]> {
    const chunks = this.getDocumentChunks();
    
    // Simple relevance scoring based on content similarity
    // In a production environment, you'd want to use proper embeddings and vector similarity
    const scoredChunks = chunks.map(chunk => ({
      chunk,
      score: this.calculateRelevance(chunk.content, prompt)
    }));

    // Sort by relevance score
    scoredChunks.sort((a, b) => b.score - a.score);

    // Return top 3 most relevant chunks
    return scoredChunks.slice(0, 3).map(sc => sc.chunk);
  }

  // Highlight relevant sections in the editor
  public highlightChunks(chunks: TextChunk[]): void {
    // Remove any existing highlights
    this.editor.commands.unsetHighlight();

    // Add new highlights
    chunks.forEach(chunk => {
      this.editor.commands.setTextSelection({
        from: chunk.startPos,
        to: chunk.endPos
      });
      this.editor.commands.setHighlight();
    });
  }

  private getNodeType(typeName: string): TextChunk['type'] {
    switch (typeName) {
      case 'heading':
        return 'heading';
      case 'paragraph':
        return 'paragraph';
      case 'bulletList':
      case 'orderedList':
        return 'list';
      case 'blockquote':
        return 'blockquote';
      default:
        return 'paragraph';
    }
  }

  private calculateRelevance(content: string, prompt: string): number {
    const contentWords = new Set(content.toLowerCase().split(/\s+/));
    const promptWords = new Set(prompt.toLowerCase().split(/\s+/));
    
    let matchCount = 0;
    promptWords.forEach(word => {
      if (contentWords.has(word)) matchCount++;
    });

    return matchCount / promptWords.size;
  }
}
