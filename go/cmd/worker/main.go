// P7 Distributed Computing — worker runtime (Go, separate process).
//
// Registers with the control plane, polls for tasks (work-stealing),
// executes them, and reports completion. Heartbeats keep the node
// marked available; the control plane marks dead nodes and requeues
// their tasks on partition/failure.
//
// Build/run (where Go is installed):
//   go run ./cmd/worker
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"
)

const controlPlane = "http://localhost:8080"

type Task struct {
	ID      string `json:"id"`
	NodeID  string `json:"node_id,omitempty"`
	Status  string `json:"status"`
	Payload string `json:"payload"`
}

func register(nodeID string) {
	body, _ := json.Marshal(map[string]string{"id": nodeID})
	_, err := http.Post(controlPlane+"/nodes", "application/json", bytes.NewReader(body))
	if err != nil {
		log.Printf("register failed: %v", err)
	}
}

func heartbeat(nodeID string) {
	body, _ := json.Marshal(map[string]string{"id": nodeID})
	_, _ = http.Post(controlPlane+"/nodes", "application/json", bytes.NewReader(body))
}

// claim fetches the next queued task for this node.
func claim(nodeID string) *Task {
	resp, err := http.Get(controlPlane + "/tasks?node=" + nodeID)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusNoContent {
		return nil
	}
	var t Task
	if json.NewDecoder(resp.Body).Decode(&t) != nil {
		return nil
	}
	return &t
}

// execute runs the task payload (simulated compute).
func execute(t *Task) error {
	log.Printf("executing %s: %s", t.ID, t.Payload)
	time.Sleep(50 * time.Millisecond)
	return nil
}

func complete(t *Task) {
	_, _ = http.Post(controlPlane+"/tasks/complete?id="+t.ID, "application/json", nil)
}

func main() {
	nodeID := fmt.Sprintf("worker-%d", time.Now().UnixNano())
	register(nodeID)
	go func() {
		for range time.Tick(5 * time.Second) {
			heartbeat(nodeID)
		}
	}()
	for {
		t := claim(nodeID)
		if t == nil {
			time.Sleep(1 * time.Second)
			continue
		}
		if err := execute(t); err != nil {
			log.Printf("task %s failed: %v", t.ID, err)
			continue
		}
		complete(t)
	}
}

var _ = io.Discard
