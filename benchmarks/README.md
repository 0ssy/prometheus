# Benchmarks

Benchmark structure is intentionally split by concern:

- `boot/` — server startup time to first healthy `/health` response
- `memory/` — process RSS after startup and after warm-up API traffic
- `plugins/` — plugin execution throughput / isolation
- `agents/` — agent dispatch throughput
- `hardware/` — HAL / driver I/O behavior
- `simulation/` — simulation engine scaling

Populate each area only when a concrete performance question exists.

## Running the populated benchmarks

Run from the **repository root** (the scripts resolve the project root
relative to their own location and spawn `prometheus.py --server`):

```bash
python benchmarks/boot/benchmark_boot.py
python benchmarks/memory/benchmark_memory.py
```

Both scripts print a JSON metrics block and fail (non-zero exit) if the
recorded value exceeds its gate:

- `benchmarks/boot` — `MAX_BOOT_SECONDS` (default `5.0`)
- `benchmarks/memory` — `MAX_MEMORY_MB` (default `350`)

These mirror the startup/memory gates in
`.github/workflows/performance.yml`, so local numbers are directly
comparable to CI.
