export enum Protocol {
  GPIO = "GPIO",
  Serial = "Serial",
  USB = "USB",
  I2C = "I2C",
  SPI = "SPI",
  CAN = "CAN",
  JTAG = "JTAG",
  Bluetooth = "Bluetooth",
  Network = "Network",
}

export type SafetyLevel = "safe" | "unsafe" | "critical";

export interface HalTraitMethod {
  name: string;
  signature: string;
}

export interface HalTraitDefinition {
  name: string;
  methods: HalTraitMethod[];
  safety_level: SafetyLevel;
}

export interface DriverManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  protocols: Protocol[];
  hal_traits: HalTraitDefinition[];
  entrypoint: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export function validateDriverManifest(manifest: unknown): ValidationResult {
  const errors: string[] = [];

  if (!manifest || typeof manifest !== "object") {
    return { valid: false, errors: ["manifest must be an object"] };
  }

  const m = manifest as Partial<DriverManifest>;

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
  if (!Array.isArray(m.protocols)) {
    errors.push("protocols is required and must be an array");
  }
  if (!Array.isArray(m.hal_traits)) {
    errors.push("hal_traits is required and must be an array");
  } else {
    m.hal_traits.forEach((t, i) => {
      if (!t || typeof t.name !== "string") {
        errors.push(`hal_traits[${i}].name is required`);
      }
      if (!t || !Array.isArray(t.methods)) {
        errors.push(`hal_traits[${i}].methods must be an array`);
      }
      if (!t || typeof t.safety_level !== "string") {
        errors.push(`hal_traits[${i}].safety_level is required`);
      }
    });
  }
  if (typeof m.entrypoint !== "string" || m.entrypoint.trim().length === 0) {
    errors.push("entrypoint is required and must be a non-empty string");
  }

  return { valid: errors.length === 0, errors };
}

export function createDefaultDriverManifest(id: string, name: string, author: string): DriverManifest {
  return {
    id,
    name,
    version: "0.1.0",
    description: `${name} driver`,
    author,
    protocols: [Protocol.USB],
    hal_traits: [],
    entrypoint: "libdriver.so",
  };
}
