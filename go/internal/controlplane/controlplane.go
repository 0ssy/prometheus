package controlplane

import (
	"log"
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

// Store is the persistence contract the control plane uses to keep nodes
// and tasks durable. It is satisfied by a small adapter in the control
// plane command that wraps prometheus/internal/persistence.Store. The
// control plane keeps an in-memory mirror for fast reads and uses the
// store for durability.
type Store interface {
	RegisterNode(n Node) error
	Heartbeat(id string) error
	ListNodes() ([]Node, error)
	SubmitTask(payload string) (*Task, error)
	ClaimTask(nodeID string) (*Task, error)
	CompleteTask(id, status string) error
	ListTasks(status string) ([]Task, error)
}

type ControlPlane struct {
	mu       sync.Mutex
	nodes    map[string]*Node
	tasks    []*Task
	nextTask int

	store Store
}

// NewControlPlane returns an in-memory control plane (no persistence).
func NewControlPlane() *ControlPlane {
	return &ControlPlane{nodes: map[string]*Node{}}
}

// NewControlPlaneWithStore returns a control plane backed by a persistence
// store. On construction it hydrates its in-memory mirror from the store so
// previously registered nodes and queued/running tasks survive restarts.
func NewControlPlaneWithStore(store Store) (*ControlPlane, error) {
	cp := &ControlPlane{nodes: map[string]*Node{}, store: store}
	nodes, err := store.ListNodes()
	if err != nil {
		return nil, err
	}
	for _, n := range nodes {
		cp.nodes[n.ID] = &Node{ID: n.ID, LastSeen: n.LastSeen, Available: n.Available}
	}
	tasks, err := store.ListTasks("")
	if err != nil {
		return nil, err
	}
	for _, t := range tasks {
		cp.tasks = append(cp.tasks, &Task{ID: t.ID, NodeID: t.NodeID, Status: t.Status, Payload: t.Payload})
		cp.nextTask = maxInt(cp.nextTask, parseSeq(t.ID))
	}
	return cp, nil
}

func (cp *ControlPlane) RegisterNode(id string) {
	cp.mu.Lock()
	node := &Node{ID: id, LastSeen: time.Now(), Available: true}
	cp.nodes[id] = node
	cp.mu.Unlock()
	if cp.store != nil {
		if err := cp.store.RegisterNode(*node); err != nil {
			persistenceLog("register-node", err)
		}
	}
}

// Heartbeat records a liveness ping for a node, creating it if unknown.
func (cp *ControlPlane) Heartbeat(id string) {
	cp.mu.Lock()
	if n, ok := cp.nodes[id]; ok {
		n.LastSeen = time.Now()
		n.Available = true
	} else {
		cp.nodes[id] = &Node{ID: id, LastSeen: time.Now(), Available: true}
	}
	cp.mu.Unlock()
	if cp.store != nil {
		if err := cp.store.Heartbeat(id); err != nil {
			persistenceLog("heartbeat", err)
		}
	}
}

func (cp *ControlPlane) ListNodes() []*Node {
	cp.mu.Lock()
	defer cp.mu.Unlock()
	out := make([]*Node, 0, len(cp.nodes))
	for _, n := range cp.nodes {
		out = append(out, n)
	}
	return out
}

func (cp *ControlPlane) SubmitTask(payload string) *Task {
	cp.mu.Lock()
	cp.nextTask++
	t := &Task{ID: taskID(cp.nextTask), Status: "queued", Payload: payload}
	cp.tasks = append(cp.tasks, t)
	cp.mu.Unlock()
	if cp.store != nil {
		if pt, err := cp.store.SubmitTask(payload); err != nil {
			persistenceLog("submit-task", err)
		} else if pt != nil {
			t.ID = pt.ID
		}
	}
	return t
}

func (cp *ControlPlane) ClaimTask(nodeID string) *Task {
	cp.mu.Lock()
	var claimed *Task
	for _, t := range cp.tasks {
		if t.Status == "queued" {
			t.Status = "running"
			t.NodeID = nodeID
			claimed = t
			break
		}
	}
	cp.mu.Unlock()
	if claimed != nil && cp.store != nil {
		if pt, err := cp.store.ClaimTask(nodeID); err != nil {
			persistenceLog("claim-task", err)
		} else if pt != nil {
			claimed.ID = pt.ID
			claimed.Status = pt.Status
			claimed.NodeID = pt.NodeID
		}
	}
	return claimed
}

func (cp *ControlPlane) CompleteTask(id string) {
	cp.CompleteTaskStatus(id, "done")
}

// CompleteTaskStatus marks a task with the given terminal status.
func (cp *ControlPlane) CompleteTaskStatus(id, status string) {
	cp.mu.Lock()
	for _, t := range cp.tasks {
		if t.ID == id {
			t.Status = status
		}
	}
	cp.mu.Unlock()
	if cp.store != nil {
		if err := cp.store.CompleteTask(id, status); err != nil {
			persistenceLog("complete-task", err)
		}
	}
}

func taskID(n int) string {
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

// persistenceLog records a non-fatal persistence error.
func persistenceLog(op string, err error) {
	if err != nil {
		log.Printf("controlplane persistence %s: %v", op, err)
	}
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// parseSeq recovers the integer sequence from a task id (base-10 string).
func parseSeq(id string) int {
	n := 0
	for _, c := range id {
		if c < '0' || c > '9' {
			continue
		}
		n = n*10 + int(c-'0')
	}
	return n
}
