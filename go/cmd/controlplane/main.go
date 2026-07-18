// P7 Distributed Computing — control plane (Go, separate process).
//
// Owns the node registry and task queue. Workers register over HTTP and
// poll for tasks; the Python side submits work via gRPC/HTTP and falls
// back to a local scheduler when this service is unavailable.
//
// State (nodes, tasks) is persisted to BoltDB so the service survives
// restarts; a graceful shutdown flushes and closes the database.
//
// Build/run (where Go is installed):
//   go run ./cmd/controlplane
//
// NOTE: the production boundary is gRPC; this stdlib HTTP implementation
// is the runnable reference (no external deps) and is wrapped by the Rust
// client in src-tauri.
package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"prometheus/internal/controlplane"
	"prometheus/internal/mdns"
	"prometheus/internal/persistence"
)

const dbPath = "controlplane.db"

func timeNow() time.Time { return time.Now() }

// storeAdapter bridges persistence.Store to controlplane.Store.
type storeAdapter struct{ *persistence.Store }

func (a *storeAdapter) RegisterNode(n controlplane.Node) error {
	return a.Store.RegisterNode(persistence.Node{ID: n.ID, LastSeen: n.LastSeen, Available: n.Available})
}

func (a *storeAdapter) ListNodes() ([]controlplane.Node, error) {
	ns, err := a.Store.ListNodes()
	if err != nil {
		return nil, err
	}
	out := make([]controlplane.Node, 0, len(ns))
	for _, n := range ns {
		out = append(out, controlplane.Node{ID: n.ID, LastSeen: n.LastSeen, Available: n.Available})
	}
	return out, nil
}

func (a *storeAdapter) SubmitTask(payload string) (*controlplane.Task, error) {
	t, err := a.Store.SubmitTask(payload)
	if err != nil || t == nil {
		return nil, err
	}
	return &controlplane.Task{ID: t.ID, NodeID: t.NodeID, Status: t.Status, Payload: t.Payload}, nil
}

func (a *storeAdapter) ClaimTask(nodeID string) (*controlplane.Task, error) {
	t, err := a.Store.ClaimTask(nodeID)
	if err != nil || t == nil {
		return nil, err
	}
	return &controlplane.Task{ID: t.ID, NodeID: t.NodeID, Status: t.Status, Payload: t.Payload}, nil
}

func (a *storeAdapter) ListTasks(status string) ([]controlplane.Task, error) {
	ts, err := a.Store.ListTasks(status)
	if err != nil {
		return nil, err
	}
	out := make([]controlplane.Task, 0, len(ts))
	for _, t := range ts {
		out = append(out, controlplane.Task{ID: t.ID, NodeID: t.NodeID, Status: t.Status, Payload: t.Payload})
	}
	return out, nil
}

func main() {
	store, err := persistence.Open(dbPath)
	if err != nil {
		log.Fatalf("open persistence: %v", err)
	}
	defer store.Close()

	cp, err := controlplane.NewControlPlaneWithStore(&storeAdapter{Store: store})
	if err != nil {
		log.Fatalf("hydrate control plane: %v", err)
	}
	log.Printf("loaded %d nodes from BoltDB", len(cp.ListNodes()))

	disc := mdns.New("controlplane-1", "controlplane", "localhost:8080")
	if err := disc.Start(); err != nil {
		log.Printf("mdns start: %v", err)
	} else {
		defer disc.Stop()
		log.Printf("mdns discovery started; known peers: %d", len(disc.Peers()))
	}

	startGRPC(cp)

	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("ok")) })
	mux.HandleFunc("/nodes", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			var n controlplane.Node
			if err := json.NewDecoder(r.Body).Decode(&n); err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
			cp.RegisterNode(n.ID)
			w.WriteHeader(http.StatusCreated)
			return
		}
		nodes := cp.ListNodes()
		json.NewEncoder(w).Encode(nodes)
	})
	mux.HandleFunc("/nodes/heartbeat", func(w http.ResponseWriter, r *http.Request) {
		id := r.URL.Query().Get("id")
		if id == "" {
			http.Error(w, "id required", http.StatusBadRequest)
			return
		}
		cp.Heartbeat(id)
		w.WriteHeader(http.StatusOK)
	})
	mux.HandleFunc("/tasks", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			var payload string
			if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
			t := cp.SubmitTask(payload)
			w.WriteHeader(http.StatusCreated)
			json.NewEncoder(w).Encode(t)
			return
		}
		t := cp.ClaimTask(r.URL.Query().Get("node"))
		if t == nil {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		json.NewEncoder(w).Encode(t)
	})
	mux.HandleFunc("/tasks/complete", func(w http.ResponseWriter, r *http.Request) {
		id := r.URL.Query().Get("id")
		status := r.URL.Query().Get("status")
		if status == "" {
			status = "done"
		}
		cp.CompleteTaskStatus(id, status)
		w.WriteHeader(http.StatusOK)
	})

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		log.Println("control plane listening on :8080")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf("http serve: %v", err)
		}
	}()

	// Graceful shutdown: flush state to disk before exiting.
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGINT, syscall.SIGTERM)
	<-stop
	log.Println("shutting down; saving state...")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("http shutdown: %v", err)
	}
	if err := store.Close(); err != nil {
		log.Printf("persistence close: %v", err)
	}
	log.Println("state saved; bye")
}
