const decoder = new TextDecoder();
const encoder = new TextEncoder();

export function ndjsonToSseStream(stream: ReadableStream<Uint8Array>): ReadableStream<Uint8Array> {
    return new ReadableStream({
        async start(controller) {
            const reader = stream.getReader();
            let buffer = "";

            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split("\n");
                    buffer = lines.pop() ?? "";

                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (trimmed) {
                            controller.enqueue(encoder.encode(`data: ${trimmed}\n\n`));
                        }
                    }
                }

                const trailing = buffer.trim();
                if (trailing) {
                    controller.enqueue(encoder.encode(`data: ${trailing}\n\n`));
                }
            } catch (error) {
                const message = error instanceof Error ? error.message : "Unknown stream error";
                controller.enqueue(encoder.encode(`event: error\ndata: ${JSON.stringify({ error: message })}\n\n`));
            } finally {
                controller.enqueue(encoder.encode("event: done\ndata: {}\n\n"));
                controller.close();
            }
        },
    });
}

export function sseResponse(stream: ReadableStream<Uint8Array>): Response {
    return new Response(ndjsonToSseStream(stream), {
        headers: {
            "content-type": "text/event-stream; charset=utf-8",
            "cache-control": "no-cache, no-transform",
            connection: "keep-alive",
        },
    });
}
