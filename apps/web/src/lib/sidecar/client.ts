import {
    type ChunkableDocumentElement,
    type ContentType,
    parseChunkResponse,
    parseExtractedDocument,
} from "@sourcelab/shared-types";

export interface SidecarExtractRequest {
    sourceId: string;
    contentType: ContentType;
    filePath?: string;
    sourceUrl?: string;
}

export interface SidecarChunkRequest {
    sourceId: string;
    elements: ChunkableDocumentElement[];
    chunkSize: number;
    chunkOverlap: number;
}

const DEFAULT_SIDECAR_BASE_URL = "http://127.0.0.1:8001";

function getSidecarBaseUrl(): string {
    return process.env.SIDECAR_BASE_URL ?? DEFAULT_SIDECAR_BASE_URL;
}

export async function extractWithSidecar(request: SidecarExtractRequest) {
    const response = await fetch(`${getSidecarBaseUrl()}/extract/file`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        const body = await response.text();
        throw new Error(`Sidecar extraction failed (${response.status}): ${body}`);
    }

    const payload: unknown = await response.json();
    return parseExtractedDocument(payload);
}

export async function chunkWithSidecar(request: SidecarChunkRequest) {
    const response = await fetch(`${getSidecarBaseUrl()}/chunk`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        const body = await response.text();
        throw new Error(`Sidecar chunking failed (${response.status}): ${body}`);
    }

    const payload: unknown = await response.json();
    return parseChunkResponse(payload);
}
