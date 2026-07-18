package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/prometheus-eng/cloud/internal/store"
	"github.com/prometheus-eng/cloud/internal/tunnel"
)

var (
	bucketTunnels = []byte("tunnels")
	storeDB       *store.Store
)

func main() {
	db, err := store.NewStore("tunnel.db", bucketTunnels)
	if err != nil {
		log.Fatalf("open persistence: %v", err)
	}
	storeDB = db
	defer db.Close()

	// Restore tunnel state references from BoltDB (the live SSH connections
	// cannot be resumed, but their metadata is durable and listed on startup).
	restoreTunnels()

	r := http.NewServeMux()

	r.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	r.HandleFunc("/v1/tunnel/list", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		statuses := tunnel.ListActiveTunnels()
		json.NewEncoder(w).Encode(map[string]any{"tunnels": statuses})
	})

	r.HandleFunc("/v1/tunnel/create", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		var req struct {
			SSHAddr     string `json:"ssh_addr"`
			SSHUser     string `json:"ssh_user"`
			SSHPassword string `json:"ssh_password"`
			SSHKeyPath  string `json:"ssh_key_path"`
			RemoteAddr  string `json:"remote_addr"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(map[string]string{"error": "invalid body: " + err.Error()})
			return
		}
		if strings.TrimSpace(req.SSHAddr) == "" || strings.TrimSpace(req.SSHUser) == "" || strings.TrimSpace(req.RemoteAddr) == "" {
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(map[string]string{"error": "ssh_addr, ssh_user, and remote_addr are required"})
			return
		}
		if strings.TrimSpace(req.SSHPassword) == "" && strings.TrimSpace(req.SSHKeyPath) == "" {
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(map[string]string{"error": "ssh_password or ssh_key_path is required"})
			return
		}

		t, err := tunnel.CreateTunnel(tunnel.TunnelConfig{
			RemoteAddr:  req.RemoteAddr,
			SSHAddr:     req.SSHAddr,
			SSHUser:     req.SSHUser,
			SSHPassword: req.SSHPassword,
			SSHKeyPath:  req.SSHKeyPath,
		})
		if err != nil {
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
			return
		}

		persistTunnel(t.ID, map[string]any{
			"id":          t.ID,
			"local_addr":  t.LocalAddr,
			"remote_addr": t.RemoteAddr,
			"ssh_addr":    t.SSHAddr,
			"ssh_user":    t.SSHUser,
			"created_at":  t.CreatedAt.Format(time.RFC3339),
			"active":      true,
		})

		resp := map[string]any{
			"id":          t.ID,
			"local_addr":  t.LocalAddr,
			"remote_addr": t.RemoteAddr,
			"ssh_addr":    t.SSHAddr,
			"ssh_user":    t.SSHUser,
			"created_at":  t.CreatedAt.Format(time.RFC3339),
		}
		json.NewEncoder(w).Encode(resp)
	})

	r.HandleFunc("/v1/tunnel/close", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		var req struct {
			ID string `json:"id"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(map[string]string{"error": "invalid body: " + err.Error()})
			return
		}
		t, ok := tunnel.GetTunnel(req.ID)
		if !ok {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]string{"error": "tunnel not found"})
			return
		}
		if err := t.Close(); err != nil {
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
			return
		}
		persistTunnel(req.ID, map[string]any{
			"id":          t.ID,
			"local_addr":  t.LocalAddr,
			"remote_addr": t.RemoteAddr,
			"ssh_addr":    t.SSHAddr,
			"ssh_user":    t.SSHUser,
			"created_at":  t.CreatedAt.Format(time.RFC3339),
			"active":      false,
		})
		json.NewEncoder(w).Encode(map[string]string{"status": "closed", "id": req.ID})
	})

	server := &http.Server{Addr: ":8083", Handler: r}
	go func() {
		fmt.Println("tunnel service listening on :8083")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf("http serve: %v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGINT, syscall.SIGTERM)
	<-stop
	log.Println("shutting down; saving state...")
	if err := server.Close(); err != nil {
		log.Printf("http close: %v", err)
	}
	if err := db.Close(); err != nil {
		log.Printf("persistence close: %v", err)
	}
	log.Println("state saved; bye")
}

func persistTunnel(id string, record map[string]any) {
	if storeDB == nil {
		return
	}
	if err := storeDB.PutJSON(bucketTunnels, []byte(id), record); err != nil {
		log.Printf("persist tunnel %s: %v", id, err)
	}
}

func restoreTunnels() {
	if storeDB == nil {
		return
	}
	n := 0
	_ = storeDB.ForEach(bucketTunnels, func(key []byte, value json.RawMessage) error {
		n++
		return nil
	})
	if n > 0 {
		log.Printf("loaded %d tunnel records from BoltDB (live connections are not resumed)", n)
	}
}
