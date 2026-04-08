export const ELEMENT_TYPES = [
    "heading",
    "paragraph",
    "table",
    "image",
    "code",
    "list",
] as const;

export const CONTENT_TYPES = [
    "pdf",
    "docx",
    "md",
    "txt",
    "html",
    "url",
    "youtube",
    "image",
] as const;

export type ElementType = (typeof ELEMENT_TYPES)[number];
export type ContentType = (typeof CONTENT_TYPES)[number];

export interface DocumentMetadata {
    author?: string;
    pageCount?: number;
    createdAt?: string;
    extractedAt: string;
}

export interface DocumentElement {
    type: ElementType;
    content: string;
    position: number;
    page?: number;
    level?: number;
    metadata?: Record<string, unknown>;
}

export interface ExtractedDocument {
    sourceId: string;
    title: string;
    language?: string;
    contentType: ContentType;
    metadata: DocumentMetadata;
    elements: DocumentElement[];
}

function isObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function isStringRecord(value: unknown): value is Record<string, unknown> {
    return isObject(value) && !Array.isArray(value);
}

export function isElementType(value: unknown): value is ElementType {
    return typeof value === "string" && ELEMENT_TYPES.includes(value as ElementType);
}

export function isContentType(value: unknown): value is ContentType {
    return typeof value === "string" && CONTENT_TYPES.includes(value as ContentType);
}

export function isDocumentElement(value: unknown): value is DocumentElement {
    if (!isObject(value)) {
        return false;
    }

    if (!isElementType(value.type)) {
        return false;
    }

    if (typeof value.content !== "string" || typeof value.position !== "number") {
        return false;
    }

    if (value.page !== undefined && typeof value.page !== "number") {
        return false;
    }

    if (value.level !== undefined && typeof value.level !== "number") {
        return false;
    }

    return value.metadata === undefined || isStringRecord(value.metadata);
}

export function isExtractedDocument(value: unknown): value is ExtractedDocument {
    if (!isObject(value)) {
        return false;
    }

    if (
        typeof value.sourceId !== "string" ||
        typeof value.title !== "string" ||
        !isContentType(value.contentType) ||
        !Array.isArray(value.elements)
    ) {
        return false;
    }

    if (value.language !== undefined && typeof value.language !== "string") {
        return false;
    }

    if (!isObject(value.metadata) || typeof value.metadata.extractedAt !== "string") {
        return false;
    }

    if (value.metadata.author !== undefined && typeof value.metadata.author !== "string") {
        return false;
    }

    if (value.metadata.pageCount !== undefined && typeof value.metadata.pageCount !== "number") {
        return false;
    }

    if (value.metadata.createdAt !== undefined && typeof value.metadata.createdAt !== "string") {
        return false;
    }

    return value.elements.every(isDocumentElement);
}

export function parseExtractedDocument(value: unknown): ExtractedDocument {
    if (!isExtractedDocument(value)) {
        throw new Error("Invalid ExtractedDocument payload");
    }

    return value;
}
