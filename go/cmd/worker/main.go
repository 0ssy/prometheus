// P7 Distributed Computing — worker runtime (Go, separate process).
//
// Registers with the control plane, polls for tasks (work-stealing),
// executes them, and reports completion. Heartbeats keep the node
// marked available; the control plane marks dead nodes and requeues
// their tasks on partition/failure.
//
// Build/run (where Go is installed):
//   go run ./cmd/worker
//   go run ./cmd/worker -ssh
package main

import (
	"bytes"
	"encoding/json"
	"flag"
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

func executeLocal(t *Task) error {
	log.Printf("executing %s: %s", t.ID, t.Payload)
	time.Sleep(50 * time.Millisecond)
	return nil
}

func complete(t *Task) {
	_, _ = http.Post(controlPlane+"/tasks/complete?id="+t.ID, "application/json", nil)
}

func main() {
	sshMode := flag.Bool("ssh", false, "execute tasks over SSH instead of locally")
	flag.Parse()

	nodeID := fmt.Sprintf("worker-%d", time.Now().UnixNano())
	register(nodeID)

	go func() {
		for range time.Tick(5 * time.Second) {
			heartbeat(nodeID)
		}
	}()

	if *sshMode {
		executor, err := newSSHExecutor()
		if err != nil {
			log.Fatalf("ssh init: %v", err)
		}
		defer executor.close()
		for {
			t := claim(nodeID)
			if t == nil {
				time.Sleep(1 * time.Second)
				continue
			}
			out, err := executor.run(t.Payload)
			if err != nil {
				log.Printf("task %s failed: %v", t.ID, err)
				continue
			}
			log.Printf("task %s output: %s", t.ID, out)
			complete(t)
		}
		return
	}

	for {
		t := claim(nodeID)
		if t == nil {
			time.Sleep(1 * time.Second)
			continue
		}
		if err := executeLocal(t); err != nil {
			log.Printf("task %s failed: %v", t.ID, err)
			continue
		}
		complete(t)
	}
}

var _ = io.Discard
