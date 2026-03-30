export type ElementType = "heading" | "paragraph" | "table" | "image" | "code" | "list";

export interface DocumentElement {
    type: ElementType;
    content: string;
    page?: number;
    position: number;
    level?: number;       // heading level
    metadata?: Record<string, unknown>;
}

export interface ExtractedDocument {
    sourceId: string;
    title: string;
    language: string;
    contentType: string;
    metadata: {
        author?: string;
        pageCount?: number;
        createdAt?: string;
        extractedAt: string;
    };
    elements: DocumentElement[];
}
