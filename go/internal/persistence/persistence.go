// P7 Distributed Computing — BoltDB persistence layer.
//
// Wraps a single *bbolt.DB for the control plane, billing, and usage
// metering services. State that was previously in-memory (nodes, tasks,
// billing events, usage snapshots) is now durable across restarts so the
// P7/P8 services satisfy their Phase 8 "persistent rather than in-memory"
// Definition of Done.
package persistence

import (
	"encoding/json"
	"errors"
	"log"
	"sync"
	"time"

	bolt "go.etcd.io/bbolt"
)

// Bucket names used by the persistence layer.
var (
	bucketNodes       = []byte("nodes")
	bucketTasks       = []byte("tasks")
	bucketBilling     = []byte("billing_events")
	bucketUsageSnap   = []byte("usage_snapshots")
	bucketMeta        = []byte("meta")
	keyTaskSeq        = []byte("task_seq")
	keyNodeHeartbeat  = []byte("last_heartbeat")
)

// Store is a thin concurrency-safe wrapper around a *bbolt.DB.
type Store struct {
	db   *bolt.DB
	mu   sync.Mutex // serializes writes that need read-modify-write
	path string
}

// Open opens (or creates) the BoltDB file at path and ensures all buckets
// exist. The caller is responsible for calling Close, typically via a
// graceful-shutdown hook.
func Open(path string) (*Store, error) {
	db, err := bolt.Open(path, 0o600, &bolt.Options{Timeout: 5 * time.Second})
	if err != nil {
		return nil, err
	}
	s := &Store{db: db, path: path}
	if err := s.ensureBuckets(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return s, nil
}

// Path returns the database file path.
func (s *Store) Path() string { return s.path }

// DB exposes the underlying database for advanced callers.
func (s *Store) DB() *bolt.DB { return s.db }

// Close flushes and closes the underlying database.
func (s *Store) Close() error {
	if s.db == nil {
		return nil
	}
	return s.db.Close()
}

func (s *Store) ensureBuckets() error {
	return s.db.Update(func(tx *bolt.Tx) error {
		for _, b := range [][]byte{bucketNodes, bucketTasks, bucketBilling, bucketUsageSnap, bucketMeta} {
			if _, err := tx.CreateBucketIfNotExists(b); err != nil {
				return err
			}
		}
		return nil
	})
}

// ---------------------------------------------------------------- Nodes ----

// Node mirrors controlplane.Node for storage.
type Node struct {
	ID        string    `json:"id"`
	LastSeen  time.Time `json:"last_seen"`
	Available bool      `json:"available"`
}

// RegisterNode creates or refreshes a node record with an updated heartbeat.
func (s *Store) RegisterNode(n Node) error {
	if n.ID == "" {
		return errors.New("persistence: node id required")
	}
	if n.LastSeen.IsZero() {
		n.LastSeen = time.Now()
	}
	data, err := json.Marshal(n)
	if err != nil {
		return err
	}
	return s.db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket(bucketNodes)
		if err := b.Put([]byte(n.ID), data); err != nil {
			return err
		}
		// Track the most recent heartbeat time globally (useful for stats).
		mb := tx.Bucket(bucketMeta)
		hb, _ := json.Marshal(n.LastSeen)
		return mb.Put(keyNodeHeartbeat, hb)
	})
}

// Heartbeat updates only the LastSeen timestamp for an existing node,
// creating the node (unavailable) if it does not exist yet.
func (s *Store) Heartbeat(id string) error {
	if id == "" {
		return errors.New("persistence: node id required")
	}
	now := time.Now()
	return s.db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket(bucketNodes)
		var n Node
		if v := b.Get([]byte(id)); v != nil {
			if err := json.Unmarshal(v, &n); err != nil {
				return err
			}
		}
		n.ID = id
		n.LastSeen = now
		data, err := json.Marshal(n)
		if err != nil {
			return err
		}
		return b.Put([]byte(id), data)
	})
}

// ListNodes returns every registered node.
func (s *Store) ListNodes() ([]Node, error) {
	out := []Node{}
	err := s.db.View(func(tx *bolt.Tx) error {
		return tx.Bucket(bucketNodes).ForEach(func(k, v []byte) error {
			var n Node
			if err := json.Unmarshal(v, &n); err != nil {
				return err
			}
			out = append(out, n)
			return nil
		})
	})
	return out, err
}

// LastHeartbeat returns the most recent heartbeat time recorded, or the
// zero time if none exists.
func (s *Store) LastHeartbeat() (time.Time, error) {
	var t time.Time
	err := s.db.View(func(tx *bolt.Tx) error {
		v := tx.Bucket(bucketMeta).Get(keyNodeHeartbeat)
		if v == nil {
			return nil
		}
		return json.Unmarshal(v, &t)
	})
	return t, err
}

// ---------------------------------------------------------------- Tasks ----

// Task mirrors controlplane.Task for storage.
type Task struct {
	ID     string `json:"id"`
	NodeID string `json:"node_id,omitempty"`
	Status string `json:"status"` // queued|running|done|failed
	Payload string `json:"payload"`
}

// SubmitTask appends a task and returns it with a freshly assigned sequence
// id. The sequence counter is stored in meta so ids are stable across
// restarts.
func (s *Store) SubmitTask(payload string) (*Task, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	var seq int
	if err := s.db.View(func(tx *bolt.Tx) error {
		v := tx.Bucket(bucketMeta).Get(keyTaskSeq)
		if v != nil {
			return json.Unmarshal(v, &seq)
		}
		return nil
	}); err != nil {
		return nil, err
	}

	seq++
	t := &Task{ID: taskID(seq), Status: "queued", Payload: payload}
	data, err := json.Marshal(t)
	if err != nil {
		return nil, err
	}
	err = s.db.Update(func(tx *bolt.Tx) error {
		if err := tx.Bucket(bucketTasks).Put([]byte(t.ID), data); err != nil {
			return err
		}
		b, _ := json.Marshal(seq)
		return tx.Bucket(bucketMeta).Put(keyTaskSeq, b)
	})
	if err != nil {
		return nil, err
	}
	return t, nil
}

// ClaimTask atomically finds the next queued task and marks it running for
// the given node, returning nil if the queue is empty.
func (s *Store) ClaimTask(nodeID string) (*Task, error) {
	var claimed *Task
	err := s.db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket(bucketTasks)
		cur := b.Cursor()
		for k, v := cur.First(); k != nil; k, v = cur.Next() {
			var t Task
			if err := json.Unmarshal(v, &t); err != nil {
				return err
			}
			if t.Status == "queued" {
				t.Status = "running"
				t.NodeID = nodeID
				data, err := json.Marshal(t)
				if err != nil {
					return err
				}
				if err := b.Put(k, data); err != nil {
					return err
				}
				claimed = &t
				return nil
			}
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return claimed, nil
}

// CompleteTask marks a task done (or failed). Unknown ids are a no-op.
func (s *Store) CompleteTask(id, status string) error {
	if status == "" {
		status = "done"
	}
	return s.db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket(bucketTasks)
		v := b.Get([]byte(id))
		if v == nil {
			return nil
		}
		var t Task
		if err := json.Unmarshal(v, &t); err != nil {
			return err
		}
		t.Status = status
		data, err := json.Marshal(t)
		if err != nil {
			return err
		}
		return b.Put([]byte(id), data)
	})
}

// ListTasks returns all tasks, optionally filtered by status.
func (s *Store) ListTasks(status string) ([]Task, error) {
	out := []Task{}
	err := s.db.View(func(tx *bolt.Tx) error {
		return tx.Bucket(bucketTasks).ForEach(func(k, v []byte) error {
			var t Task
			if err := json.Unmarshal(v, &t); err != nil {
				return err
			}
			if status == "" || t.Status == status {
				out = append(out, t)
			}
			return nil
		})
	})
	return out, err
}

// ------------------------------------------------------------ Billing -----

// BillingEvent is a single metered usage event.
type BillingEvent struct {
	TenantID  string    `json:"tenant_id"`
	Metric    string    `json:"metric"`
	Quantity  float64   `json:"quantity"`
	UnitPrice float64   `json:"unit_price"`
	At        time.Time `json:"at"`
}

// AppendBillingEvent stores a usage event. Each event is keyed by a
// monotonically increasing sequence so events are never overwritten.
func (s *Store) AppendBillingEvent(e BillingEvent) error {
	if e.TenantID == "" || e.Metric == "" {
		return errors.New("persistence: tenant_id and metric required")
	}
	if e.At.IsZero() {
		e.At = time.Now()
	}
	s.mu.Lock()
	defer s.mu.Unlock()

	var seq int
	if err := s.db.View(func(tx *bolt.Tx) error {
		n := tx.Bucket(bucketBilling).Stats().KeyN
		seq = n
		return nil
	}); err != nil {
		return err
	}
	key := []byte(eventKey(seq))
	data, err := json.Marshal(e)
	if err != nil {
		return err
	}
	return s.db.Update(func(tx *bolt.Tx) error {
		return tx.Bucket(bucketBilling).Put(key, data)
	})
}

// ListBillingEvents returns every stored billing event.
func (s *Store) ListBillingEvents() ([]BillingEvent, error) {
	out := []BillingEvent{}
	err := s.db.View(func(tx *bolt.Tx) error {
		return tx.Bucket(bucketBilling).ForEach(func(k, v []byte) error {
			var e BillingEvent
			if err := json.Unmarshal(v, &e); err != nil {
				return err
			}
			out = append(out, e)
			return nil
		})
	})
	return out, err
}

// ------------------------------------------------------ Usage snapshots ----

// UsageSnapshot is a persisted per-tenant meter reading.
type UsageSnapshot struct {
	TenantID string    `json:"tenant_id"`
	Window   string    `json:"window"`
	Totals   map[string]float64 `json:"totals"`
	At       time.Time `json:"at"`
}

// SaveUsageSnapshot overwrites the snapshot for a tenant (keyed by tenant).
func (s *Store) SaveUsageSnapshot(snap UsageSnapshot) error {
	if snap.TenantID == "" {
		return errors.New("persistence: tenant_id required")
	}
	if snap.At.IsZero() {
		snap.At = time.Now()
	}
	if snap.Totals == nil {
		snap.Totals = map[string]float64{}
	}
	data, err := json.Marshal(snap)
	if err != nil {
		return err
	}
	return s.db.Update(func(tx *bolt.Tx) error {
		return tx.Bucket(bucketUsageSnap).Put([]byte(snap.TenantID), data)
	})
}

// LoadUsageSnapshots returns the most recent snapshot for every tenant.
func (s *Store) LoadUsageSnapshots() ([]UsageSnapshot, error) {
	out := []UsageSnapshot{}
	err := s.db.View(func(tx *bolt.Tx) error {
		return tx.Bucket(bucketUsageSnap).ForEach(func(k, v []byte) error {
			var snap UsageSnapshot
			if err := json.Unmarshal(v, &snap); err != nil {
				return err
			}
			out = append(out, snap)
			return nil
		})
	})
	return out, err
}

// ------------------------------------------------------------- Helpers ----

func eventKey(seq int) string { return "e:" + taskID(seq) }

// taskID formats an integer as a base-10 string (mirrors controlplane.taskID).
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

// LogError logs a persistence error without crashing the caller.
func LogError(op string, err error) {
	if err != nil {
		log.Printf("persistence %s: %v", op, err)
	}
}
