import { eq, sql } from "drizzle-orm";
import { db } from "../client";
import { projects } from "../schema";

export type Project = typeof projects.$inferSelect;
export type NewProject = Omit<typeof projects.$inferInsert, "id" | "createdAt" | "updatedAt">;
export type ProjectUpdate = Partial<Omit<typeof projects.$inferInsert, "id" | "createdAt" | "updatedAt">>;

export function findProjectById(id: string): Project | undefined {
    return db.select().from(projects).where(eq(projects.id, id)).get();
}

export function listProjects(): Project[] {
    return db.select().from(projects).all();
}

export function createProject(data: NewProject): Project {
    return db
        .insert(projects)
        .values({ ...data, id: crypto.randomUUID() })
        .returning()
        .get();
}

export function updateProject(id: string, data: ProjectUpdate): Project | undefined {
    return db
        .update(projects)
        .set({ ...data, updatedAt: sql`(datetime('now'))` })
        .where(eq(projects.id, id))
        .returning()
        .get();
}

export function deleteProject(id: string): void {
    db.delete(projects).where(eq(projects.id, id)).run();
}