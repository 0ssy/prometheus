export enum PluginPermission {
  Read = "read",
  Write = "write",
  Execute = "execute",
  Network = "network",
  Hardware = "hardware",
  Knowledge = "knowledge",
}

export interface PluginCapability {
  name: string;
  description: string;
  permissions: PluginPermission[];
}

export interface PluginEngine {
  id: string;
  version: string;
  runtime: string;
}

export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  capabilities: PluginCapability[];
  permissions: PluginPermission[];
  entrypoint: string;
  engines: PluginEngine[];
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export function validatePluginManifest(manifest: unknown): ValidationResult {
  const errors: string[] = [];

  if (!manifest || typeof manifest !== "object") {
    return { valid: false, errors: ["manifest must be an object"] };
  }

  const m = manifest as Partial<PluginManifest>;

  if (typeof m.id !== "string" || m.id.trim().length === 0) {
    errors.push("id is required and must be a non-empty string");
  }
  if (typeof m.name !== "string" || m.name.trim().length === 0) {
    errors.push("name is required and must be a non-empty string");
  }
  if (typeof m.version !== "string" || m.version.trim().length === 0) {
    errors.push("version is required and must be a non-empty string");
  }
  if (typeof m.description !== "string") {
    errors.push("description is required and must be a string");
  }
  if (typeof m.author !== "string" || m.author.trim().length === 0) {
    errors.push("author is required and must be a non-empty string");
  }
  if (!Array.isArray(m.capabilities)) {
    errors.push("capabilities is required and must be an array");
  } else {
    m.capabilities.forEach((c, i) => {
      if (!c || typeof c.name !== "string") {
        errors.push(`capabilities[${i}].name is required`);
      }
      if (!c || typeof c.description !== "string") {
        errors.push(`capabilities[${i}].description is required`);
      }
      if (!c || !Array.isArray(c.permissions)) {
        errors.push(`capabilities[${i}].permissions must be an array`);
      }
    });
  }
  if (!Array.isArray(m.permissions)) {
    errors.push("permissions is required and must be an array");
  }
  if (typeof m.entrypoint !== "string" || m.entrypoint.trim().length === 0) {
    errors.push("entrypoint is required and must be a non-empty string");
  }
  if (!Array.isArray(m.engines) || m.engines.length === 0) {
    errors.push("engines is required and must be a non-empty array");
  } else {
    m.engines.forEach((e, i) => {
      if (!e || typeof e.id !== "string") {
        errors.push(`engines[${i}].id is required`);
      }
      if (!e || typeof e.version !== "string") {
        errors.push(`engines[${i}].version is required`);
      }
      if (!e || typeof e.runtime !== "string") {
        errors.push(`engines[${i}].runtime is required`);
      }
    });
  }

  return { valid: errors.length === 0, errors };
}

export function createDefaultManifest(id: string, name: string, author: string): PluginManifest {
  return {
    id,
    name,
    version: "0.1.0",
    description: `${name} plugin`,
    author,
    capabilities: [],
    permissions: [],
    entrypoint: "index.ts",
    engines: [
      {
        id: "typescript",
        version: ">=5.0.0",
        runtime: "node",
      },
    ],
  };
}
