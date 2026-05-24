import { NextResponse } from "next/server";
import { pullOllamaModel } from "../../../../../lib/ollama/client";
import { sseResponse } from "../../../../../lib/ollama/streaming";

function parseBody(value: unknown): { model: string; insecure?: boolean } {
    if (!value || typeof value !== "object") {
        throw new Error("Request body must be an object");
    }

    const body = value as Record<string, unknown>;
    if (typeof body.model !== "string" || body.model.length === 0) {
        throw new Error("model is required");
    }

    if (body.insecure !== undefined && typeof body.insecure !== "boolean") {
        throw new Error("insecure must be a boolean");
    }

    return { model: body.model, insecure: body.insecure };
}

export async function POST(request: Request) {
    let body: { model: string; insecure?: boolean };

    try {
        body = parseBody(await request.json());
    } catch (error) {
        const message = error instanceof Error ? error.message : "Invalid request payload";
        return NextResponse.json({ error: message }, { status: 400 });
    }

    try {
        return sseResponse(await pullOllamaModel(body));
    } catch (error) {
        const message = error instanceof Error ? error.message : "Ollama pull failed";
        return NextResponse.json({ error: message }, { status: 502 });
    }
}
