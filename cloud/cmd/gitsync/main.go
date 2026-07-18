package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/prometheus-eng/cloud/internal/gitsync"
)

func main() {
	local := flag.String("local", "", "path to the local workspace git repository")
	remote := flag.String("remote", "", "remote git URL to sync against")
	branch := flag.String("branch", "main", "branch to track")
	nodeID := flag.String("node", "", "unique node identifier for this workspace")
	mode := flag.String("mode", "sync", "operation: sync | pull | push | merge")
	stateFile := flag.String("state", "", "path to a remote CRDT state file (used by merge mode)")
	flag.Parse()

	if *local == "" {
		log.Fatal("error: -local path is required")
	}
	if *nodeID == "" {
		*nodeID = hostnameOrDefault("node-unknown")
	}

	sync := gitsync.NewWorkspaceSync(*local, *remote, *branch, *nodeID)

	switch *mode {
	case "pull":
		if err := sync.Pull(); err != nil {
			log.Fatalf("pull failed: %v", err)
		}
		fmt.Println("pull: ok")

	case "push":
		if err := sync.Push(); err != nil {
			log.Fatalf("push failed: %v", err)
		}
		fmt.Println("push: ok")

	case "merge":
		remoteState := loadState(*stateFile)
		localState := loadLocalState(*local)
		baseState := gitsync.NewCrdtNodeForMerge()
		merged, err := sync.Merge(baseState, localState, remoteState)
		if err != nil {
			log.Fatalf("merge failed: %v", err)
		}
		out, _ := json.MarshalIndent(merged, "", "  ")
		fmt.Printf("merge: ok\n%s\n", out)

	case "sync":
		fallthrough
	default:
		remoteState := loadState(*stateFile)
		merged, err := sync.Sync(remoteState)
		if err != nil {
			log.Fatalf("sync failed: %v", err)
		}
		out, _ := json.MarshalIndent(merged, "", "  ")
		fmt.Printf("sync: ok\n%s\n", out)
	}
}

func hostnameOrDefault(fallback string) string {
	if h, err := os.Hostname(); err == nil && h != "" {
		return h
	}
	return fallback
}

func loadState(path string) *gitsync.SyncState {
	if path == "" {
		return gitsync.NewRemoteState("remote")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		log.Fatalf("cannot read state file %s: %v", path, err)
	}
	var state gitsync.SyncState
	if err := json.Unmarshal(data, &state); err != nil {
		log.Fatalf("cannot parse state file %s: %v", path, err)
	}
	return &state
}

func loadLocalState(localPath string) *gitsync.SyncState {
	state, err := gitsync.LoadLocalState(localPath, "node-local")
	if err != nil {
		log.Fatalf("cannot load local state: %v", err)
	}
	return state
}

var _ = time.Now
