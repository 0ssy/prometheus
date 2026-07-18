export interface StudioDefinition {
  id: string;
  name: string;
  icon: string;
  description: string;
  category: string;
  entrypoint: string;
}

export const STUDIO_CATEGORIES = [
  "robotics",
  "firmware",
  "embedded",
  "reverse_engineering",
  "security",
  "networking",
  "pcb",
  "cad",
  "ai",
  "vision",
  "audio",
  "cloud",
  "vehicle",
  "iot",
  "industrial",
] as const;

export type StudioCategory = (typeof STUDIO_CATEGORIES)[number];

export const STUDIOS: StudioDefinition[] = [
  {
    id: "robotics",
    name: "Robotics Studio",
    icon: "🤖",
    description: "Robot control, simulation, and path planning.",
    category: "robotics",
    entrypoint: "/studios/robotics",
  },
  {
    id: "firmware",
    name: "Firmware Studio",
    icon: "⚙️",
    description: "Firmware development, flashing, and boot-chain analysis.",
    category: "firmware",
    entrypoint: "/studios/firmware",
  },
  {
    id: "embedded",
    name: "Embedded Studio",
    icon: "🔌",
    description: "Embedded system configuration, RTOS, and sensor workflows.",
    category: "embedded",
    entrypoint: "/studios/embedded",
  },
  {
    id: "reverse_engineering",
    name: "Reverse Engineering Lab",
    icon: "🔍",
    description: "Binary analysis, disassembly, and vulnerability research.",
    category: "reverse_engineering",
    entrypoint: "/studios/reverse-engineering",
  },
  {
    id: "security",
    name: "Security Lab",
    icon: "🛡️",
    description: "Security auditing, penetration testing, and compliance.",
    category: "security",
    entrypoint: "/studios/security",
  },
  {
    id: "networking",
    name: "Networking Lab",
    icon: "🌐",
    description: "Network topology, packet analysis, and connectivity diagnostics.",
    category: "networking",
    entrypoint: "/studios/networking",
  },
  {
    id: "pcb",
    name: "PCB Studio",
    icon: "📟",
    description: "PCB design, routing, and signal integrity analysis.",
    category: "pcb",
    entrypoint: "/studios/pcb",
  },
  {
    id: "cad",
    name: "CAD Integration",
    icon: "📐",
    description: "CAD model management, CAM toolpath generation, and simulation.",
    category: "cad",
    entrypoint: "/studios/cad",
  },
  {
    id: "ai",
    name: "AI Lab",
    icon: "🧠",
    description: "Model management, inference, RAG indexing, and fine-tuning.",
    category: "ai",
    entrypoint: "/studios/ai",
  },
  {
    id: "vision",
    name: "Vision Lab",
    icon: "👁️",
    description: "Computer vision pipelines, SLAM, and image analysis.",
    category: "vision",
    entrypoint: "/studios/vision",
  },
  {
    id: "audio",
    name: "Audio Lab",
    icon: "🎵",
    description: "Audio signal processing, recording, and analysis.",
    category: "audio",
    entrypoint: "/studios/audio",
  },
  {
    id: "cloud",
    name: "Cloud Lab",
    icon: "☁️",
    description: "Cloud deployment, scaling, monitoring, and secrets management.",
    category: "cloud",
    entrypoint: "/studios/cloud",
  },
  {
    id: "vehicle",
    name: "Vehicle Studio",
    icon: "🚗",
    description: "Vehicle diagnostics, CAN bus, and autonomous driving stacks.",
    category: "vehicle",
    entrypoint: "/studios/vehicle",
  },
  {
    id: "iot",
    name: "IoT Lab",
    icon: "📡",
    description: "IoT device management, provisioning, and telemetry.",
    category: "iot",
    entrypoint: "/studios/iot",
  },
  {
    id: "industrial",
    name: "Industrial Automation Studio",
    icon: "🏭",
    description: "SCADA, PLC programming, and industrial network automation.",
    category: "industrial",
    entrypoint: "/studios/industrial",
  },
];

export function getStudioById(id: string): StudioDefinition | undefined {
  return STUDIOS.find((s) => s.id === id);
}

export function getStudiosByCategory(category: string): StudioDefinition[] {
  return STUDIOS.filter((s) => s.category === category);
}

export function getAllCategories(): string[] {
  return [...STUDIO_CATEGORIES];
}
