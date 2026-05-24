import { NextResponse } from "next/server";
import { embedWithOllama } from "../../../../../lib/ollama/client";

function parseBody(value: unknown) {
    if (!value || typeof value !== "object") {
        throw new Error("Request body must be an object");
    }

    const body = value as Record<string, unknown>;
    if (typeof body.model !== "string" || body.model.length === 0) {
        throw new Error("model is required");
    }

    const input = body.input;
    const validInput =
        typeof input === "string" ||
        (Array.isArray(input) && input.every((item) => typeof item === "string"));
    if (!validInput) {
        throw new Error("input must be a string or string[]");
    }

    if (body.truncate !== undefined && typeof body.truncate !== "boolean") {
        throw new Error("truncate must be a boolean");
    }

    if (body.dimensions !== undefined && typeof body.dimensions !== "number") {
        throw new Error("dimensions must be a number");
    }

    return {
        model: body.model,
        input,
        truncate: body.truncate,
        dimensions: body.dimensions,
        keep_alive: typeof body.keep_alive === "string" ? body.keep_alive : undefined,
        options: typeof body.options === "object" && body.options !== null ? body.options as Record<string, unknown> : undefined,
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
        return NextResponse.json(await embedWithOllama(body));
    } catch (error) {
        const message = error instanceof Error ? error.message : "Ollama embedding failed";
        return NextResponse.json({ error: message }, { status: 502 });
    }
}
