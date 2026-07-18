package gitsync

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"
)

// VectorClock is a per-node incrementing clock used to establish causality.
type VectorClock struct {
	clocks map[string]int
}

func NewVectorClock() *VectorClock {
	return &VectorClock{clocks: make(map[string]int)}
}

func (vc *VectorClock) Increment(nodeID string) {
	vc.clocks[nodeID]++
}

func (vc *VectorClock) Get(nodeID string) int {
	return vc.clocks[nodeID]
}

// Merge takes the element-wise maximum of two vector clocks.
func (vc *VectorClock) Merge(other *VectorClock) {
	for nodeID, count := range other.clocks {
		if count > vc.clocks[nodeID] {
			vc.clocks[nodeID] = count
		}
	}
}

func (vc *VectorClock) toDict() map[string]int {
	out := make(map[string]int, len(vc.clocks))
	for k, v := range vc.clocks {
		out[k] = v
	}
	return out
}

func vectorClockFromDict(data map[string]int) *VectorClock {
	vc := NewVectorClock()
	for k, v := range data {
		vc.clocks[k] = v
	}
	return vc
}

// GCounter is a grow-only counter (per-node increments).
type GCounter struct {
	counts map[string]int
}

func NewGCounter() *GCounter {
	return &GCounter{counts: make(map[string]int)}
}

func (c *GCounter) Increment(nodeID string, amount int) {
	c.counts[nodeID] += amount
}

func (c *GCounter) Value() int {
	sum := 0
	for _, v := range c.counts {
		sum += v
	}
	return sum
}

func (c *GCounter) merge(other *GCounter) {
	for nodeID, count := range other.counts {
		if count > c.counts[nodeID] {
			c.counts[nodeID] = count
		}
	}
}

func (c *GCounter) toDict() map[string]int {
	out := make(map[string]int, len(c.counts))
	for k, v := range c.counts {
		out[k] = v
	}
	return out
}

func gCounterFromDict(data map[string]int) *GCounter {
	g := NewGCounter()
	for k, v := range data {
		g.counts[k] = v
	}
	return g
}

// PNCounter is a positive-negative counter built from two GCounters.
type PNCounter struct {
	positive *GCounter
	negative *GCounter
}

func NewPNCounter() *PNCounter {
	return &PNCounter{positive: NewGCounter(), negative: NewGCounter()}
}

func (c *PNCounter) Increment(nodeID string, amount int) {
	c.positive.Increment(nodeID, amount)
}

func (c *PNCounter) Decrement(nodeID string, amount int) {
	c.negative.Increment(nodeID, amount)
}

func (c *PNCounter) Value() int {
	return c.positive.Value() - c.negative.Value()
}

func (c *PNCounter) merge(other *PNCounter) {
	c.positive.merge(other.positive)
	c.negative.merge(other.negative)
}

func (c *PNCounter) toDict() map[string]map[string]int {
	return map[string]map[string]int{
		"positive": c.positive.toDict(),
		"negative": c.negative.toDict(),
	}
}

func pnCounterFromDict(data map[string]map[string]int) *PNCounter {
	c := NewPNCounter()
	if p, ok := data["positive"]; ok {
		c.positive = gCounterFromDict(p)
	}
	if n, ok := data["negative"]; ok {
		c.negative = gCounterFromDict(n)
	}
	return c
}

// ORSet is an observed-removed set: adds carry unique tags, removes tombstone
// the tags that were observed at removal time.
type ORSet struct {
	elements map[string]map[string]struct{}
	removed  map[string]struct{}
}

func NewORSet() *ORSet {
	return &ORSet{
		elements: make(map[string]map[string]struct{}),
		removed:  make(map[string]struct{}),
	}
}

func (s *ORSet) Add(element string, tag string) {
	if _, ok := s.elements[element]; !ok {
		s.elements[element] = make(map[string]struct{})
	}
	s.elements[element][tag] = struct{}{}
}

func (s *ORSet) Remove(element string) {
	if tags, ok := s.elements[element]; ok {
		for tag := range tags {
			s.removed[tag] = struct{}{}
		}
		delete(s.elements, element)
	}
}

func (s *ORSet) Has(element string) bool {
	tags, ok := s.elements[element]
	if !ok {
		return false
	}
	for tag := range tags {
		if _, tomb := s.removed[tag]; !tomb {
			return true
		}
	}
	return false
}

func (s *ORSet) Elements() []string {
	var out []string
	for element, tags := range s.elements {
		for tag := range tags {
			if _, tomb := s.removed[tag]; !tomb {
				out = append(out, element)
				break
			}
		}
	}
	return out
}

func (s *ORSet) merge(other *ORSet) {
	for element, tags := range other.elements {
		if _, ok := s.elements[element]; !ok {
			s.elements[element] = make(map[string]struct{})
		}
		for tag := range tags {
			s.elements[element][tag] = struct{}{}
		}
	}
	for tag := range other.removed {
		s.removed[tag] = struct{}{}
	}
}

func (s *ORSet) toDict() map[string]interface{} {
	elems := make(map[string][]string, len(s.elements))
	for element, tags := range s.elements {
		for tag := range tags {
			elems[element] = append(elems[element], tag)
		}
	}
	removed := make([]string, 0, len(s.removed))
	for tag := range s.removed {
		removed = append(removed, tag)
	}
	return map[string]interface{}{
		"elements": elems,
		"removed":  removed,
	}
}

func orSetFromDict(data map[string]interface{}) *ORSet {
	s := NewORSet()
	if elems, ok := data["elements"].(map[string]interface{}); ok {
		for element, raw := range elems {
			if list, ok := raw.([]interface{}); ok {
				for _, t := range list {
					if tag, ok := t.(string); ok {
						s.Add(element, tag)
					}
				}
			}
		}
	}
	if rawRemoved, ok := data["removed"].([]interface{}); ok {
		for _, t := range rawRemoved {
			if tag, ok := t.(string); ok {
				s.removed[tag] = struct{}{}
			}
		}
	}
	return s
}

// LWWRegister is a last-writer-wins register using (timestamp, nodeID) tie-break.
type LWWRegister struct {
	value     interface{}
	timestamp float64
	nodeID    string
}

func NewLWWRegister() *LWWRegister {
	return &LWWRegister{}
}

func (r *LWWRegister) Set(value interface{}, timestamp float64, nodeID string) {
	if timestamp > r.timestamp || (timestamp == r.timestamp && nodeID > r.nodeID) {
		r.value = value
		r.timestamp = timestamp
		r.nodeID = nodeID
	}
}

func (r *LWWRegister) Get() interface{} {
	return r.value
}

func (r *LWWRegister) merge(other *LWWRegister) {
	if other.timestamp > r.timestamp || (other.timestamp == r.timestamp && other.nodeID > r.nodeID) {
		r.value = other.value
		r.timestamp = other.timestamp
		r.nodeID = other.nodeID
	}
}

func (r *LWWRegister) toDict() map[string]interface{} {
	return map[string]interface{}{
		"value":     r.value,
		"timestamp": r.timestamp,
		"node_id":   r.nodeID,
	}
}

func lwwRegisterFromDict(data map[string]interface{}) *LWWRegister {
	r := NewLWWRegister()
	if v, ok := data["value"]; ok {
		r.value = v
	}
	if ts, ok := data["timestamp"].(float64); ok {
		r.timestamp = ts
	}
	if n, ok := data["node_id"].(string); ok {
		r.nodeID = n
	}
	return r
}

// CrdtNode bundles the CRDT structures for a single workspace node.
type CrdtNode struct {
	NodeID       string        `json:"node_id"`
	VectorClock  *VectorClock  `json:"-"`
	Counter      *PNCounter    `json:"-"`
	Set          *ORSet        `json:"-"`
	Register     *LWWRegister  `json:"-"`
	Timestamp    float64       `json:"-"`
	VectorClockD map[string]int `json:"vector_clock"`
	CounterD     map[string]map[string]int `json:"counter"`
	SetD         map[string]interface{}    `json:"set"`
	RegisterD    map[string]interface{}    `json:"register"`
	TimestampD   float64       `json:"timestamp"`
}

func NewCrdtNode(nodeID string) *CrdtNode {
	return &CrdtNode{
		NodeID:      nodeID,
		VectorClock: NewVectorClock(),
		Counter:     NewPNCounter(),
		Set:         NewORSet(),
		Register:    NewLWWRegister(),
		Timestamp:   float64(time.Now().UnixNano()) / float64(time.Second),
	}
}

// Merge applies another node's state into this node (idempotent, commutative).
func (n *CrdtNode) Merge(other *CrdtNode) *CrdtNode {
	n.VectorClock.Merge(other.VectorClock)
	n.Counter.merge(other.Counter)
	n.Set.merge(other.Set)
	n.Register.merge(other.Register)
	if other.Timestamp > n.Timestamp {
		n.Timestamp = other.Timestamp
	}
	return n
}

// MarshalJSON emits the CRDT payload in a stable, JSON-serialisable form.
func (n *CrdtNode) MarshalJSON() ([]byte, error) {
	type alias CrdtNode
	return json.Marshal(&struct {
		VectorClock map[string]int            `json:"vector_clock"`
		Counter     map[string]map[string]int `json:"counter"`
		Set         map[string]interface{}    `json:"set"`
		Register    map[string]interface{}    `json:"register"`
		Timestamp   float64                   `json:"timestamp"`
		*alias
	}{
		VectorClock: n.VectorClock.toDict(),
		Counter:     n.Counter.toDict(),
		Set:         n.Set.toDict(),
		Register:    n.Register.toDict(),
		Timestamp:   n.Timestamp,
		alias:       (*alias)(n),
	})
}

// UnmarshalJSON reconstructs a CrdtNode from its JSON form.
func (n *CrdtNode) UnmarshalJSON(data []byte) error {
	var raw struct {
		NodeID      string                   `json:"node_id"`
		VectorClock map[string]int           `json:"vector_clock"`
		Counter     map[string]map[string]int `json:"counter"`
		Set         map[string]interface{}   `json:"set"`
		Register    map[string]interface{}   `json:"register"`
		Timestamp   float64                  `json:"timestamp"`
	}
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}
	n.NodeID = raw.NodeID
	n.VectorClock = vectorClockFromDict(raw.VectorClock)
	n.Counter = pnCounterFromDict(raw.Counter)
	n.Set = orSetFromDict(raw.Set)
	n.Register = lwwRegisterFromDict(raw.Register)
	n.Timestamp = raw.Timestamp
	return nil
}

// SyncState is the full synchronisation record persisted in a workspace repo.
type SyncState struct {
	Node    *CrdtNode `json:"node"`
	Origin  string    `json:"origin"`
	At      int64     `json:"at"`
}

// WorkspaceSync tracks a local and remote git repository and performs
// three-way merge of workspace CRDT state on conflicts.
type WorkspaceSync struct {
	mu            sync.Mutex
	LocalPath     string
	RemoteURL     string
	Branch        string
	NodeID        string
	GitBin        string
	StateFileName string
}

// NewWorkspaceSync constructs a sync handle for the given local workspace path.
func NewWorkspaceSync(localPath, remoteURL, branch, nodeID string) *WorkspaceSync {
	gitBin := "git"
	if p, err := exec.LookPath("git"); err == nil {
		gitBin = p
	}
	return &WorkspaceSync{
		LocalPath:     localPath,
		RemoteURL:     remoteURL,
		Branch:        branch,
		NodeID:        nodeID,
		GitBin:        gitBin,
		StateFileName: ".workspace_crdt.json",
	}
}

func (w *WorkspaceSync) git(args ...string) ([]byte, error) {
	cmd := exec.Command(w.GitBin, args...)
	cmd.Dir = w.LocalPath
	out, err := cmd.CombinedOutput()
	if err != nil {
		return out, fmt.Errorf("git %v: %w: %s", args, err, string(out))
	}
	return out, nil
}

func (w *WorkspaceSync) statePath() string {
	return filepath.Join(w.LocalPath, w.StateFileName)
}

// readLocalState loads the persisted CRDT state from the local workspace.
func (w *WorkspaceSync) readLocalState() (*SyncState, error) {
	data, err := os.ReadFile(w.statePath())
	if err != nil {
		if os.IsNotExist(err) {
			return &SyncState{Node: NewCrdtNode(w.NodeID), Origin: w.NodeID, At: time.Now().Unix()}, nil
		}
		return nil, err
	}
	var state SyncState
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, err
	}
	return &state, nil
}

func (w *WorkspaceSync) writeLocalState(state *SyncState) error {
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(w.statePath(), data, 0o644)
}

// Pull fetches and fast-forwards the remote branch into the local repo.
func (w *WorkspaceSync) Pull() error {
	w.mu.Lock()
	defer w.mu.Unlock()

	if _, err := w.git("fetch", "origin", w.Branch); err != nil {
		return err
	}
	if _, err := w.git("merge", "--ff-only", "origin/"+w.Branch); err != nil {
		return err
	}
	return nil
}

// Push commits the local CRDT state and publishes it to the remote branch.
func (w *WorkspaceSync) Push() error {
	w.mu.Lock()
	defer w.mu.Unlock()

	state, err := w.readLocalState()
	if err != nil {
		return err
	}
	state.At = time.Now().Unix()

	if _, err := w.git("add", w.StateFileName); err != nil {
		return err
	}
	if _, err := w.git("commit", "-m", fmt.Sprintf("crdt sync: %s", w.NodeID)); err != nil {
		// Ignore "nothing to commit" which still returns an error code.
		if _, statErr := os.Stat(w.statePath()); statErr != nil {
			return err
		}
	}
	if _, err := w.git("push", "origin", w.Branch); err != nil {
		return err
	}
	_ = state
	return nil
}

// Merge performs a three-way CRDT merge of local, base and remote state and
// writes the merged state back. The base is the last common ancestor state;
// local and remote are the diverged states. Because every structure is a CRDT,
// conflicts resolve deterministically without user intervention.
func (w *WorkspaceSync) Merge(base, local, remote *SyncState) (*SyncState, error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	merged := NewCrdtNode(w.NodeID)
	merged.Merge(local.Node)
	merged.Merge(remote.Node)
	if base != nil {
		merged.Merge(base.Node)
	}

	result := &SyncState{
		Node:   merged,
		Origin: fmt.Sprintf("%s+%s", local.Origin, remote.Origin),
		At:     time.Now().Unix(),
	}
	if err := w.writeLocalState(result); err != nil {
		return nil, err
	}
	return result, nil
}

// NewCrdtNodeForMerge returns an empty baseline node used as the three-way
// merge base when no shared ancestor state is available.
func NewCrdtNodeForMerge() *SyncState {
	return &SyncState{Node: NewCrdtNode("base"), Origin: "base", At: time.Now().Unix()}
}

// NewRemoteState builds a fresh remote state payload used by CLI/merge callers
// that provide a remote node identifier without a backing file.
func NewRemoteState(nodeID string) *SyncState {
	return &SyncState{Node: NewCrdtNode(nodeID), Origin: nodeID, At: time.Now().Unix()}
}

// LoadLocalState reads the persisted CRDT state from a workspace directory,
// returning a fresh node when none exists yet.
func LoadLocalState(localPath, nodeID string) (*SyncState, error) {
	path := filepath.Join(localPath, ".workspace_crdt.json")
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return &SyncState{Node: NewCrdtNode(nodeID), Origin: nodeID, At: time.Now().Unix()}, nil
		}
		return nil, err
	}
	var state SyncState
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, err
	}
	return &state, nil
}

// Sync is a convenience orchestration: pull, load local, merge with the remote
// state carried in remoteState, then push.
func (w *WorkspaceSync) Sync(remoteState *SyncState) (*SyncState, error) {
	if err := w.Pull(); err != nil {
		return nil, err
	}
	local, err := w.readLocalState()
	if err != nil {
		return nil, err
	}
	base := &SyncState{Node: NewCrdtNode(w.NodeID), Origin: w.NodeID, At: time.Now().Unix()}
	merged, err := w.Merge(base, local, remoteState)
	if err != nil {
		return nil, err
	}
	if err := w.Push(); err != nil {
		return nil, err
	}
	return merged, nil
}
