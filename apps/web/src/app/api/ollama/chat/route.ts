import { NextResponse } from "next/server";
import {
    chatWithOllama,
    streamChatWithOllama,
    type OllamaChatRequest,
    type OllamaMessage,
} from "../../../../../lib/ollama/client";
import { sseResponse } from "../../../../../lib/ollama/streaming";

const MESSAGE_ROLES = new Set(["system", "user", "assistant", "tool"]);

function isMessage(value: unknown): value is OllamaMessage {
    if (!value || typeof value !== "object") {
        return false;
    }

    const message = value as Record<string, unknown>;
    return (
        typeof message.role === "string" &&
        MESSAGE_ROLES.has(message.role) &&
        typeof message.content === "string" &&
        (message.images === undefined ||
            (Array.isArray(message.images) && message.images.every((image) => typeof image === "string"))) &&
        (message.tool_name === undefined || typeof message.tool_name === "string")
    );
}

function parseBody(value: unknown): OllamaChatRequest & { stream: boolean } {
    if (!value || typeof value !== "object") {
        throw new Error("Request body must be an object");
    }

    const body = value as Record<string, unknown>;
    if (typeof body.model !== "string" || body.model.length === 0) {
        throw new Error("model is required");
    }

    if (!Array.isArray(body.messages) || !body.messages.every(isMessage)) {
        throw new Error("messages must be valid Ollama chat messages");
    }

    if (body.stream !== undefined && typeof body.stream !== "boolean") {
        throw new Error("stream must be a boolean");
    }

    const think = body.think;
    const validThink =
        think === undefined ||
        typeof think === "boolean" ||
        think === "low" ||
        think === "medium" ||
        think === "high";
    if (!validThink) {
        throw new Error("think must be boolean, low, medium, or high");
    }

    const format: OllamaChatRequest["format"] =
        body.format === "json" || (typeof body.format === "object" && body.format !== null)
            ? body.format as OllamaChatRequest["format"]
            : undefined;

    return {
        model: body.model,
        messages: body.messages,
        stream: body.stream ?? true,
        format,
        options: typeof body.options === "object" && body.options !== null ? body.options as Record<string, unknown> : undefined,
        keep_alive: typeof body.keep_alive === "string" ? body.keep_alive : undefined,
        think: think as OllamaChatRequest["think"],
    };
}

export async function POST(request: Request) {
    let body: ReturnType<typeof parseBody>;

    try {
        body = parseBody(await request.json());
    } catch (error) {
        const message = error instanceof Error ? error.message : "Invalid request payload";
        return NextResponse.json({ error: message }, { status: 400 });
    }

    try {
        const { stream, ...ollamaRequest } = body;
        if (!stream) {
            return NextResponse.json(await chatWithOllama(ollamaRequest));
        }

        return sseResponse(await streamChatWithOllama(ollamaRequest));
    } catch (error) {
        const message = error instanceof Error ? error.message : "Ollama chat failed";
        return NextResponse.json({ error: message }, { status: 502 });
    }
}
