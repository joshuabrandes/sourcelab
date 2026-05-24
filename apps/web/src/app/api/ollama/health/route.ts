import { NextResponse } from "next/server";
import { getOllamaHealth } from "../../../../../lib/ollama/client";

export const dynamic = "force-dynamic";

export async function GET() {
    const health = await getOllamaHealth();
    return NextResponse.json(health, { status: health.ok ? 200 : 503 });
}
