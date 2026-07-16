// P7 Distributed Computing — control plane (Go, separate process).
//
// Owns the node registry and task queue. Workers register over HTTP and
// poll for tasks; the Python side submits work via gRPC/HTTP and falls
// back to a local scheduler when this service is unavailable.
//
// Build/run (where Go is installed):
//   go run ./cmd/controlplane
//
// NOTE: the production boundary is gRPC; this stdlib HTTP implementation
// is the runnable reference (no external deps) and is wrapped by the Rust
// client in src-tauri.
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"
)

type Node struct {
	ID        string    `json:"id"`
	LastSeen  time.Time `json:"last_seen"`
	Available bool      `json:"available"`
}

type Task struct {
	ID     string `json:"id"`
	NodeID string `json:"node_id,omitempty"`
	Status string `json:"status"` // queued|running|done|failed
	Payload string `json:"payload"`
}

type ControlPlane struct {
	mu       sync.Mutex
	nodes    map[string]*Node
	tasks    []*Task
	nextTask int
}

func NewControlPlane() *ControlPlane {
	return &ControlPlane{nodes: map[string]*Node{}}
}

func (cp *ControlPlane) registerNode(w http.ResponseWriter, r *http.Request) {
	var n Node
	if err := json.NewDecoder(r.Body).Decode(&n); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	cp.mu.Lock()
	cp.nodes[n.ID] = &Node{ID: n.ID, LastSeen: time.Now(), Available: true}
	cp.mu.Unlock()
	w.WriteHeader(http.StatusCreated)
}

func (cp *ControlPlane) listNodes(w http.ResponseWriter, r *http.Request) {
	cp.mu.Lock()
	defer cp.mu.Unlock()
	nodes := make([]*Node, 0, len(cp.nodes))
	for _, n := range cp.nodes {
		nodes = append(nodes, n)
	}
	json.NewEncoder(w).Encode(nodes)
}

func (cp *ControlPlane) submitTask(w http.ResponseWriter, r *http.Request) {
	var t Task
	if err := json.NewDecoder(r.Body).Decode(&t); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	cp.mu.Lock()
	cp.nextTask++
	t.ID = taskID(cp.nextTask)
	t.Status = "queued"
	cp.tasks = append(cp.tasks, &t)
	cp.mu.Unlock()
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(t)
}

// claimTask hands the next queued task to a worker (work-stealing).
func (cp *ControlPlane) claimTask(w http.ResponseWriter, r *http.Request) {
	cp.mu.Lock()
	defer cp.mu.Unlock()
	for _, t := range cp.tasks {
		if t.Status == "queued" {
			t.Status = "running"
			t.NodeID = r.URL.Query().Get("node")
			json.NewEncoder(w).Encode(t)
			return
		}
	}
	w.WriteHeader(http.StatusNoContent)
}

func (cp *ControlPlane) completeTask(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	cp.mu.Lock()
	defer cp.mu.Unlock()
	for _, t := range cp.tasks {
		if t.ID == id {
			t.Status = "done"
		}
	}
	w.WriteHeader(http.StatusOK)
}

func main() {
	cp := NewControlPlane()
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("ok")) })
	mux.HandleFunc("/nodes", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			cp.registerNode(w, r)
			return
		}
		cp.listNodes(w, r)
	})
	mux.HandleFunc("/tasks", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			cp.submitTask(w, r)
			return
		}
		cp.claimTask(w, r)
	})
	mux.HandleFunc("/tasks/complete", cp.completeTask)
	log.Println("control plane listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", mux))
}

func taskID(n int) string { return "task-" + itoa(n) }

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var b [20]byte
	i := len(b)
	for n > 0 {
		i--
		b[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		b[i] = '-'
	}
	return string(b[i:])
}
