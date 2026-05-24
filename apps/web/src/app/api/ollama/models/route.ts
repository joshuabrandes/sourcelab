import { NextResponse } from "next/server";
import {
    listOllamaModels,
    listRunningOllamaModels,
} from "../../../../../lib/ollama/client";

export const dynamic = "force-dynamic";

export async function GET() {
    const [models, runningModels] = await Promise.all([
        listOllamaModels(),
        listRunningOllamaModels(),
    ]);

    return NextResponse.json({ models, runningModels });
}
