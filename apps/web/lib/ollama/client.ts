export type OllamaMessageRole = "system" | "user" | "assistant" | "tool";

export interface OllamaMessage {
    role: OllamaMessageRole;
    content: string;
    images?: string[];
    tool_name?: string;
}

export interface OllamaModelDetails {
    format?: string;
    family?: string;
    families?: string[];
    parameter_size?: string;
    quantization_level?: string;
}

export interface OllamaModel {
    name: string;
    model: string;
    modified_at: string;
    size: number;
    digest: string;
    details?: OllamaModelDetails;
}

export interface OllamaChatRequest {
    model: string;
    messages: OllamaMessage[];
    format?: "json" | Record<string, unknown>;
    options?: Record<string, unknown>;
    keep_alive?: string;
    think?: boolean | "low" | "medium" | "high";
}

export interface OllamaChatChunk {
    model?: string;
    created_at?: string;
    message?: OllamaMessage;
    done: boolean;
    total_duration?: number;
    load_duration?: number;
    prompt_eval_count?: number;
    prompt_eval_duration?: number;
    eval_count?: number;
    eval_duration?: number;
}

export interface OllamaEmbedRequest {
    model: string;
    input: string | string[];
    truncate?: boolean;
    dimensions?: number;
    keep_alive?: string;
    options?: Record<string, unknown>;
}

export interface OllamaEmbedResponse {
    model: string;
    embeddings: number[][];
    total_duration?: number;
    load_duration?: number;
    prompt_eval_count?: number;
}

export interface OllamaPullRequest {
    model: string;
    insecure?: boolean;
}

export interface OllamaPullChunk {
    status: string;
    digest?: string;
    total?: number;
    completed?: number;
}

export class OllamaApiError extends Error {
    constructor(
        message: string,
        readonly status: number,
        readonly body: string,
    ) {
        super(message);
        this.name = "OllamaApiError";
    }
}

const DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434";
const DEFAULT_TIMEOUT_MS = 30_000;

function getOllamaBaseUrl(): string {
    return process.env.OLLAMA_BASE_URL ?? DEFAULT_OLLAMA_BASE_URL;
}

async function requestJson<T>(
    path: string,
    init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
    const { timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchInit } = init ?? {};
    const response = await fetch(`${getOllamaBaseUrl()}${path}`, {
        ...fetchInit,
        signal: fetchInit.signal ?? AbortSignal.timeout(timeoutMs),
    });

    if (!response.ok) {
        const body = await response.text();
        throw new OllamaApiError(`Ollama request failed (${response.status})`, response.status, body);
    }

    return response.json() as Promise<T>;
}

async function requestStream(
    path: string,
    init: RequestInit & { timeoutMs?: number },
): Promise<ReadableStream<Uint8Array>> {
    const { timeoutMs = 0, ...fetchInit } = init;
    const response = await fetch(`${getOllamaBaseUrl()}${path}`, {
        ...fetchInit,
        signal: fetchInit.signal ?? (timeoutMs > 0 ? AbortSignal.timeout(timeoutMs) : undefined),
    });

    if (!response.ok) {
        const body = await response.text();
        throw new OllamaApiError(`Ollama request failed (${response.status})`, response.status, body);
    }

    if (!response.body) {
        throw new Error("Ollama returned an empty streaming response");
    }

    return response.body;
}

export async function getOllamaVersion(): Promise<{ version: string }> {
    return requestJson("/api/version", { method: "GET" });
}

export async function getOllamaHealth(): Promise<{ ok: true; version: string } | { ok: false; error: string }> {
    try {
        const { version } = await getOllamaVersion();
        return { ok: true, version };
    } catch (error) {
        return { ok: false, error: error instanceof Error ? error.message : "Unknown Ollama error" };
    }
}

export async function listOllamaModels(): Promise<OllamaModel[]> {
    const response = await requestJson<{ models: OllamaModel[] }>("/api/tags", { method: "GET" });
    return response.models;
}

export async function listRunningOllamaModels(): Promise<OllamaModel[]> {
    const response = await requestJson<{ models: OllamaModel[] }>("/api/ps", { method: "GET" });
    return response.models;
}

export async function embedWithOllama(request: OllamaEmbedRequest): Promise<OllamaEmbedResponse> {
    return requestJson("/api/embed", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request),
        timeoutMs: 120_000,
    });
}

export async function chatWithOllama(request: OllamaChatRequest): Promise<OllamaChatChunk> {
    return requestJson("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ ...request, stream: false }),
        timeoutMs: 120_000,
    });
}

export async function streamChatWithOllama(request: OllamaChatRequest): Promise<ReadableStream<Uint8Array>> {
    return requestStream("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ ...request, stream: true }),
    });
}

export async function pullOllamaModel(request: OllamaPullRequest): Promise<ReadableStream<Uint8Array>> {
    return requestStream("/api/pull", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ ...request, stream: true }),
    });
}
