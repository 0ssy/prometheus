package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/prometheus-eng/cloud/internal/billing"
	"github.com/prometheus-eng/cloud/internal/store"
	"github.com/prometheus-eng/cloud/internal/tenant"
)

var (
	bucketTenants = []byte("tenants")
	bucketRecords = []byte("billing_records")
)

var (
	meter   *billing.Meter
	storeDB *store.Store
	mu      sync.Mutex
)

func main() {
	db, err := store.NewStore("billing.db", bucketTenants, bucketRecords)
	if err != nil {
		log.Fatalf("open persistence: %v", err)
	}
	storeDB = db
	defer db.Close()

	meter = billing.NewMeter(30 * 24 * time.Hour)

	// Load persisted tenants; seed a demo tenant if none exist.
	loaded := loadTenants()
	if len(loaded) == 0 {
		seed := &tenant.Tenant{ID: "tenant-demo", Name: "Demo Org", Created: time.Now().Unix()}
		if err := persistTenant(seed); err != nil {
			log.Printf("seed tenant: %v", err)
		}
	} else {
		log.Printf("loaded %d tenants from BoltDB", len(loaded))
	}

	r := http.NewServeMux()
	r.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, `{"status":"ok"}`)
	})
	r.HandleFunc("/v1/billing/invoice", func(w http.ResponseWriter, r *http.Request) {
		tenantID := r.URL.Query().Get("tenant_id")
		snapshot := meter.Snapshot(tenantID)
		items := make([]map[string]any, 0)
		for res, qty := range snapshot {
			items = append(items, map[string]any{"resource": res, "quantity": qty, "unit": "req", "price_usd": 0.001})
		}
		record := map[string]any{"tenant_id": tenantID, "currency": "USD", "items": items, "at": time.Now().Format(time.RFC3339)}
		if _, err := storeDB.AppendJSON(bucketRecords, record); err != nil {
			log.Printf("persist billing record: %v", err)
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"tenant_id": tenantID, "currency": "USD", "items": items})
	})
	r.HandleFunc("/v1/billing/usage", func(w http.ResponseWriter, r *http.Request) {
		tenantID := r.URL.Query().Get("tenant_id")
		snapshot := meter.Snapshot(tenantID)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"tenant_id": tenantID, "usage": snapshot})
	})

	server := &http.Server{Addr: ":8082", Handler: r}
	go func() {
		fmt.Println("billing service listening on :8082")
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

func loadTenants() []*tenant.Tenant {
	out := []*tenant.Tenant{}
	_ = storeDB.ForEach(bucketTenants, func(key []byte, value json.RawMessage) error {
		var t tenant.Tenant
		if err := json.Unmarshal(value, &t); err != nil {
			return nil
		}
		out = append(out, &t)
		return nil
	})
	return out
}

func persistTenant(t *tenant.Tenant) error {
	return storeDB.PutJSON(bucketTenants, []byte(t.ID), t)
}
