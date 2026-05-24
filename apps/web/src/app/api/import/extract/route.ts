import {
    type ContentType,
    isContentType,
    isElementType,
} from "@sourcelab/shared-types";
import { NextResponse } from "next/server";
import {
    createSource,
    findProjectById,
    insertChunks,
    insertElements,
    updateSourceStatus,
} from "../../../../../lib/db/repositories";
import { chunkWithSidecar, extractWithSidecar } from "@/lib/sidecar/client";

interface ImportExtractRequest {
    projectId: string;
    contentType: ContentType;
    title?: string;
    filePath?: string;
    sourceUrl?: string;
    language?: string;
}

function parseRequestBody(body: unknown): ImportExtractRequest {
    if (!body || typeof body !== "object") {
        throw new Error("Request body must be an object");
    }

    const candidate = body as Record<string, unknown>;
    const { projectId, contentType, title, filePath, sourceUrl, language } = candidate;

    if (typeof projectId !== "string" || projectId.length === 0) {
        throw new Error("projectId is required");
    }

    if (!isContentType(contentType)) {
        throw new Error("contentType is invalid");
    }

    if (title !== undefined && typeof title !== "string") {
        throw new Error("title must be a string");
    }

    if (filePath !== undefined && typeof filePath !== "string") {
        throw new Error("filePath must be a string");
    }

    if (sourceUrl !== undefined && typeof sourceUrl !== "string") {
        throw new Error("sourceUrl must be a string");
    }

    if (language !== undefined && typeof language !== "string") {
        throw new Error("language must be a string");
    }

    return {
        projectId,
        contentType,
        title,
        filePath,
        sourceUrl,
        language,
    };
}

export async function POST(request: Request) {
    let parsed: ImportExtractRequest;

    try {
        parsed = parseRequestBody(await request.json());
    } catch (error) {
        const message = error instanceof Error ? error.message : "Invalid request payload";
        return NextResponse.json({ error: message }, { status: 400 });
    }

    const project = findProjectById(parsed.projectId);
    if (!project) {
        return NextResponse.json({ error: "Project not found" }, { status: 404 });
    }

    const source = createSource({
        projectId: parsed.projectId,
        title: parsed.title ?? "Untitled source",
        contentType: parsed.contentType,
        originalPath: parsed.filePath,
        sourceUrl: parsed.sourceUrl,
        language: parsed.language,
        metadata: null,
        status: "processing",
        errorMessage: null,
        tokenCount: null,
        chunkCount: null,
        processedAt: null,
    });

    try {
        const extracted = await extractWithSidecar({
            sourceId: source.id,
            contentType: parsed.contentType,
            filePath: parsed.filePath,
            sourceUrl: parsed.sourceUrl,
        });

        const insertedElements = insertElements(
            extracted.elements.map((element) => ({
                sourceId: source.id,
                type: element.type,
                level: element.level ?? null,
                content: element.content,
                page: element.page ?? null,
                position: element.position,
                metadata: element.metadata ? JSON.stringify(element.metadata) : null,
            })),
        );

        const chunked = await chunkWithSidecar({
            sourceId: source.id,
            chunkSize: project.chunkSize ?? 512,
            chunkOverlap: project.chunkOverlap ?? 64,
            elements: insertedElements.map((element) => {
                if (!isElementType(element.type)) {
                    throw new Error(`Invalid extracted element type: ${element.type}`);
                }

                return {
                    id: element.id,
                    type: element.type,
                    content: element.content,
                    position: element.position,
                    page: element.page ?? undefined,
                    level: element.level ?? undefined,
                    metadata: element.metadata ? JSON.parse(element.metadata) : undefined,
                };
            }),
        });

        const chunks = insertChunks(
            chunked.chunks.map((chunk) => ({
                sourceId: chunk.sourceId,
                content: chunk.content,
                tokenCount: chunk.tokenCount,
                startElement: chunk.startElement,
                endElement: chunk.endElement,
                headingContext: chunk.headingContext ?? null,
                page: chunk.page ?? null,
                position: chunk.position,
            })),
        );

        const updated = updateSourceStatus(source.id, "ready", {
            chunkCount: chunks.length,
        });

        return NextResponse.json({
            sourceId: source.id,
            status: updated?.status ?? "ready",
            elementCount: extracted.elements.length,
            chunkCount: chunks.length,
            title: extracted.title,
        });
    } catch (error) {
        const message = error instanceof Error ? error.message : "Extraction failed";
        updateSourceStatus(source.id, "error", { errorMessage: message });
        return NextResponse.json(
            { sourceId: source.id, status: "error", error: message },
            { status: 502 },
        );
    }
}
