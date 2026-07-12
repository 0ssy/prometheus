# Labs — Roadmap

Planned experimental areas for Prometheus. Work landing here starts as a
spike, graduates to RFC/ADR, and then moves into a production module.

| Lab area         | Focus                                                          | Target phase     |
|------------------|----------------------------------------------------------------|------------------|
| `labs/robotics`  | Kinematics, actuator drivers, motion planning                  | Beta+            |
| `labs/vision`    | Camera ingestion, OCR, inspection pipelines                    | Beta+            |
| `labs/voice`     | Audio I/O, speech-to-text, voice commands                      | Beta+            |
| `labs/firmware`  | Boot-chain analysis, partition inspection, update flows         | Gamma            |
| `labs/quantum`   | Quantum-safe algorithms, entropy sources                       | Future           |
| `labs/ai`        | On-device inference, model quantization, local LLM coupling     | RC1+/Post-RC1   |
| `labs/recovery`  | Self-healing strategies, rollback policies, disaster recovery   | Delta/Epsilon    |

Rules:

- Fast experiments are allowed.
- Production modules are not edited directly from labs prototypes.
- Successful experiments get promoted to RFC/ADR and then moved into
  production modules.
- Failed experiments remain documented or are archived.
