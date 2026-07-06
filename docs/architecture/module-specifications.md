# Module Specifications

## Alpha — Foundation

### Plugin Manager
- **Responsibility**: Discover, register, and execute plugins.
- **Interface**: `register(plugin)`, `run(name, context)`, `list_plugins()`.
- **Contract**: Plugins receive a context dict and return a result dict.
- **Failure mode**: Unhandled exceptions propagate to the caller.

### Agent Manager
- **Responsibility**: Dispatch agents with task context.
- **Interface**: `register(agent)`, `dispatch(name, task, context)`, `list_agents()`.
- **Contract**: Agents receive a task dict and context, return a result dict.
- **Failure mode**: Agent exceptions are logged and re-raised.

### Memory Store
- **Responsibility**: Remember and recall tagged entries.
- **Interface**: `remember(db, content, tag, source)`, `recall(db, tag, limit)`.
- **Contract**: Entries are immutable once written. `created_at` is set by the DB.
- **Failure mode**: DB errors propagate as SQLAlchemy exceptions.

### Reasoning Graph
- **Responsibility**: Assert and query knowledge-graph facts.
- **Interface**: `assert_fact(db, subject, predicate, object)`, `query_facts(db, subject)`.
- **Contract**: Facts are append-only. No update or delete operations.
- **Failure mode**: DB errors propagate as SQLAlchemy exceptions.

## Beta — Devices

### Device Registry
- **Responsibility**: Track connected devices by transport.
- **Interface**: `register(device)`, `get(device_id)`, `unregister(device_id)`, `list()`.
- **Contract**: Devices must implement the `Device` ABC. Registry holds references,
  not copies.
- **Failure mode**: `get()` returns `None` for unknown devices.

### Device ABC
- **Responsibility**: Define the contract every transport must implement.
- **Interface**: `connect()`, `disconnect()`, `read()`, `write(payload)`, `status()`.
- **Contract**: `connect()` is idempotent. `status()` returns JSON-serializable dict.
- **Failure mode**: Implementations raise `ConnectionError` when not connected.

### Simulated Device
- **Responsibility**: Fake hardware for testing.
- **Interface**: Extends `Device`. Adds `latency_seconds`, `failure_rate`.
- **Contract**: Echoes writes as reads. Injects latency and random failures.
- **Failure mode**: Raises `ConnectionError` on simulated failure or when disconnected.

### Serial Device
- **Responsibility**: Real serial-port communication.
- **Interface**: Extends `Device`. Adds `port`, `baudrate`.
- **Contract**: Uses `pyserial` for I/O. Blocks on reads/writes.
- **Failure mode**: Raises `SerialException` on port errors.

## Gamma — Firmware & Boot

### Partition Mapper
- **Responsibility**: Read GPT/MBR partition tables from raw disks/images.
- **Interface**: `read_partition_table(disk_path, ownership_declared, sector_size)`.
- **Contract**: READ-ONLY. Returns `PartitionTable` with scheme and entries.
- **Failure mode**: Returns `scheme="unknown"` on corrupt/missing GPT signature.

### Firmware Inspector
- **Responsibility**: Fingerprint firmware images.
- **Interface**: `inspect_firmware(path, ownership_declared)`.
- **Contract**: Returns `FirmwareReport` with size, SHA-256, and format.
- **Failure mode**: Returns `format="unknown_format"` for unrecognized binaries.

### Boot Chain Analyzer
- **Responsibility**: Verify Ed25519 signatures over firmware.
- **Interface**: `analyze_boot_chain(firmware_bytes, signature, public_key_bytes)`.
- **Contract**: Returns `BootChainResult` with status valid/invalid/unknown.
- **Failure mode**: Returns `status="unknown"` on malformed input.

### Recovery Planner
- **Responsibility**: Produce ordered official recovery options.
- **Interface**: `plan_recovery(device_id, boot_chain_status, partition_scheme)`.
- **Contract**: Never executes anything. Returns `RecoveryPlan` with steps.
- **Failure mode**: Always returns at least one step; never empty plan.

## Delta — Digital Twin

### Digital Twin Engine
- **Responsibility**: Aggregate knowledge-graph facts into a nine-field twin.
- **Interface**: `build_twin(db, device_id)`.
- **Contract**: Twin is a materialized view, not a second source of truth.
- **Failure mode**: Returns `state="unknown"` when no connection events exist.

## Epsilon — Autonomous Engineering

### Autonomous Engineering Engine
- **Responsibility**: Plan idea-to-deployment pipelines and suggest improvements.
- **Interface**: `create_plan(plan_id, idea, db)`, `suggest_improvements(db)`.
- **Contract**: Plans are structured, auditable, and recorded as facts.
- **Failure mode**: Returns draft plan with all capability gaps listed.
