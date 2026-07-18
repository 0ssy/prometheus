package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/prometheus-eng/cloud/internal/billing"
	"github.com/prometheus-eng/cloud/internal/middleware"
	"github.com/prometheus-eng/cloud/internal/store"
)

var (
	bucketAPIKeys = []byte("api_keys")
	bucketUsage   = []byte("usage")
)

var (
	apiKeysMu sync.Mutex
	apiKeys   = map[string]string{}
	meter     = billing.NewMeter(24 * time.Hour)
	storeDB   *store.Store
)

func loadAPIKeys() {
	if storeDB == nil {
		return
	}
	apiKeysMu.Lock()
	defer apiKeysMu.Unlock()
	_ = storeDB.ForEach(bucketAPIKeys, func(key []byte, value json.RawMessage) error {
		var tenantID string
		if err := json.Unmarshal(value, &tenantID); err != nil {
			return nil
		}
		apiKeys[string(key)] = tenantID
		return nil
	})
	log.Printf("loaded %d api keys from BoltDB", len(apiKeys))
}

func persistAPIKey(key, tenantID string) {
	apiKeysMu.Lock()
	apiKeys[key] = tenantID
	apiKeysMu.Unlock()
	if storeDB != nil {
		if err := storeDB.PutJSON(bucketAPIKeys, []byte(key), tenantID); err != nil {
			log.Printf("persist api key: %v", err)
		}
	}
}

func main() {
	db, err := store.NewStore("gateway.db", bucketAPIKeys, bucketUsage)
	if err != nil {
		log.Fatalf("open persistence: %v", err)
	}
	storeDB = db
	defer db.Close()

	loadAPIKeys()
	if len(apiKeys) == 0 {
		persistAPIKey("demo-key", "tenant-demo")
	}

	r := http.NewServeMux()
	r.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	r.HandleFunc("/v1/hardware/probe", func(w http.ResponseWriter, r *http.Request) {
		tenantID, _ := middleware.TenantIDFromContext(r.Context())
		meter.Record(billing.UsageEvent{TenantID: tenantID, Resource: "hardware.probe", Quantity: 1, Unit: "req", At: time.Now()})
		persistUsage(tenantID, "hardware.probe")
		json.NewEncoder(w).Encode(map[string]any{"tenant": tenantID, "transport": r.URL.Query().Get("transport"), "target": r.URL.Query().Get("target")})
	})

	r.HandleFunc("/v1/simulation/run", func(w http.ResponseWriter, r *http.Request) {
		tenantID, _ := middleware.TenantIDFromContext(r.Context())
		meter.Record(billing.UsageEvent{TenantID: tenantID, Resource: "simulation.run", Quantity: 1, Unit: "req", At: time.Now()})
		persistUsage(tenantID, "simulation.run")
		json.NewEncoder(w).Encode(map[string]string{"status": "queued", "tenant": tenantID})
	})

	r.HandleFunc("/v1/billing/usage", func(w http.ResponseWriter, r *http.Request) {
		tenantID, _ := middleware.TenantIDFromContext(r.Context())
		usage := meter.Snapshot(tenantID)
		json.NewEncoder(w).Encode(map[string]any{"tenant": tenantID, "usage": usage, "window": "24h"})
	})

	stack := middleware.RateLimiter(100, 200)(middleware.TenantAuth(apiKeys)(r))

	server := &http.Server{Addr: ":8080", Handler: stack}
	go func() {
		log.Println("cloud gateway listening on :8080")
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

// persistUsage appends a usage event to BoltDB so the meter is durable.
func persistUsage(tenantID, resource string) {
	if storeDB == nil {
		return
	}
	_, err := storeDB.AppendJSON(bucketUsage, map[string]any{
		"tenant_id": tenantID,
		"resource":  resource,
		"quantity":  1,
		"unit":      "req",
		"at":        time.Now().Format(time.RFC3339),
	})
	if err != nil {
		log.Printf("persist usage: %v", err)
	}
}
