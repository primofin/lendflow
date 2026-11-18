/** Friendly names for generated API types (src/lib/api/schema.d.ts, from the backend OpenAPI). */

import type { components } from "./schema";

type Schemas = components["schemas"];

export type User = Schemas["UserOut"];
export type Role = User["role"];
