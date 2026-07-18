import { Protocol, SafetyLevel, HalTraitDefinition } from "./driver-manifest";

export interface DriverManifestParsed {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  protocols: Protocol[];
  hal_traits: HalTraitDefinition[];
  entrypoint: string;
}

export interface DeviceConnection {
  deviceId: string;
  driverId: string;
  transport: string;
  connected: boolean;
  safetyLevel: SafetyLevel;
}

export interface ReadRequest {
  length?: number;
}

export interface ReadResponse {
  data: Uint8Array;
  bytesRead: number;
}

export interface WriteRequest {
  data: Uint8Array | string;
}

export interface WriteResponse {
  bytesWritten: number;
}

export interface DriverHealth {
  driverId: string;
  connected: boolean;
  lastError?: string;
}

export class DriverRuntime {
  private manifests: Map<string, DriverManifestParsed> = new Map();
  private connections: Map<string, DeviceConnection> = new Map();
  private safetyPolicies: Map<string, SafetyLevel> = new Map();

  async loadManifest(manifest: DriverManifestParsed): Promise<void> {
    this.manifests.set(manifest.id, manifest);
    for (const trait of manifest.hal_traits) {
      this.safetyPolicies.set(`${manifest.id}::${trait.name}`, trait.safety_level);
    }
  }

  async connect(driverId: string, deviceId: string, transport: string): Promise<DeviceConnection> {
    const manifest = this.manifests.get(driverId);
    if (!manifest) {
      throw new Error(`driver ${driverId} not loaded`);
    }
    if (!manifest.protocols.includes(transport as Protocol)) {
      throw new Error(`driver ${driverId} does not support transport ${transport}`);
    }

    const connection: DeviceConnection = {
      deviceId,
      driverId,
      transport,
      connected: true,
      safetyLevel: this.resolveSafetyLevel(driverId, "read"),
    };

    this.connections.set(deviceId, connection);
    return connection;
  }

  async disconnect(deviceId: string): Promise<void> {
    const connection = this.connections.get(deviceId);
    if (!connection) return;
    connection.connected = false;
    this.connections.delete(deviceId);
  }

  async read(deviceId: string, request: ReadRequest = {}): Promise<ReadResponse> {
    const connection = this.connections.get(deviceId);
    if (!connection || !connection.connected) {
      throw new Error(`device ${deviceId} not connected`);
    }

    this.enforceSafety(deviceId, "read");

    const length = request.length ?? 256;
    const response = await fetch(`/api/drivers/${encodeURIComponent(connection.driverId)}/devices/${encodeURIComponent(deviceId)}/read`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ length }),
    });

    if (!response.ok) {
      throw new Error(`read failed: ${response.status}`);
    }

    const data = await response.json() as { data?: number[] };
    const bytes = new Uint8Array(data.data ?? []);
    return { data: bytes, bytesRead: bytes.length };
  }

  async write(deviceId: string, request: WriteRequest): Promise<WriteResponse> {
    const connection = this.connections.get(deviceId);
    if (!connection || !connection.connected) {
      throw new Error(`device ${deviceId} not connected`);
    }

    this.enforceSafety(deviceId, "write");

    let payload: Uint8Array;
    if (typeof request.data === "string") {
      payload = new TextEncoder().encode(request.data);
    } else {
      payload = request.data;
    }

    const response = await fetch(`/api/drivers/${encodeURIComponent(connection.driverId)}/devices/${encodeURIComponent(deviceId)}/write`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: Array.from(payload) }),
    });

    if (!response.ok) {
      throw new Error(`write failed: ${response.status}`);
    }

    const data = await response.json() as { bytes_written?: number };
    return { bytesWritten: data.bytes_written ?? payload.length };
  }

  getConnection(deviceId: string): DeviceConnection | undefined {
    return this.connections.get(deviceId);
  }

  getHealth(driverId: string): DriverHealth {
    const connectedDevices = Array.from(this.connections.values()).filter((c) => c.driverId === driverId);
    return {
      driverId,
      connected: connectedDevices.length > 0 && connectedDevices.every((c) => c.connected),
    };
  }

  listDrivers(): DriverManifestParsed[] {
    return Array.from(this.manifests.values());
  }

  listConnections(): DeviceConnection[] {
    return Array.from(this.connections.values());
  }

  getHalTraits(driverId: string): HalTraitDefinition[] {
    return this.manifests.get(driverId)?.hal_traits ?? [];
  }

  private resolveSafetyLevel(driverId: string, operation: string): SafetyLevel {
    const traitKey = `${driverId}::${operation}`;
    const policy = this.safetyPolicies.get(traitKey);
    if (policy) return policy;
    const manifest = this.manifests.get(driverId);
    if (!manifest || manifest.hal_traits.length === 0) return "safe";
    return manifest.hal_traits[0].safety_level;
  }

  private enforceSafety(deviceId: string, operation: string): void {
    const connection = this.connections.get(deviceId);
    if (!connection) throw new Error(`device ${deviceId} not connected`);

    const level = this.resolveSafetyLevel(connection.driverId, operation);
    if (level === "critical") {
      throw new Error(`operation ${operation} on device ${deviceId} requires explicit approval (critical safety level)`);
    }
  }
}

export const driverRuntime = new DriverRuntime();
