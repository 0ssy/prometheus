module prometheus

go 1.23

require (
	golang.org/x/crypto v0.21.0
	google.golang.org/grpc v1.64.0
)

require go.etcd.io/bbolt v1.3.8

require (
	golang.org/x/net v0.22.0 // indirect
	golang.org/x/sys v0.18.0 // indirect
	golang.org/x/text v0.14.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20240318140521-94a12d6c2237 // indirect
	google.golang.org/protobuf v1.36.11
)

// Prometheus distributed/cloud services (P7, P8).
//
// Run individually (Go toolchain required; not installed in the
// implementation sandbox):
//   go run ./cmd/controlplane
//   go run ./cmd/worker
//   go run ./cmd/billing
//
// The gRPC front-end and SSH worker require the modules above. Run
// `go mod tidy` in a toolchain-present environment to populate the full
// dependency graph (incl. google.golang.org/protobuf, golang.org/x/sys,
// golang.org/x/net, etc.).
