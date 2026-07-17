package main

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/prometheus-eng/cloud/internal/billing"
	"github.com/prometheus-eng/cloud/internal/middleware"
)

var apiKeys = map[string]string{
	"demo-key": "tenant-demo",
}

var meter = billing.NewMeter(24 * time.Hour)

func main() {
	r := http.NewServeMux()
	r.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	r.HandleFunc("/v1/hardware/probe", func(w http.ResponseWriter, r *http.Request) {
		tenantID, _ := middleware.TenantIDFromContext(r.Context())
		meter.Record(billing.UsageEvent{TenantID: tenantID, Resource: "hardware.probe", Quantity: 1, Unit: "req", At: time.Now()})
		json.NewEncoder(w).Encode(map[string]any{"tenant": tenantID, "transport": r.URL.Query().Get("transport"), "target": r.URL.Query().Get("target")})
	})

	r.HandleFunc("/v1/simulation/run", func(w http.ResponseWriter, r *http.Request) {
		tenantID, _ := middleware.TenantIDFromContext(r.Context())
		meter.Record(billing.UsageEvent{TenantID: tenantID, Resource: "simulation.run", Quantity: 1, Unit: "req", At: time.Now()})
		json.NewEncoder(w).Encode(map[string]string{"status": "queued", "tenant": tenantID})
	})

	r.HandleFunc("/v1/billing/usage", func(w http.ResponseWriter, r *http.Request) {
		tenantID, _ := middleware.TenantIDFromContext(r.Context())
		usage := meter.Snapshot(tenantID)
		json.NewEncoder(w).Encode(map[string]any{"tenant": tenantID, "usage": usage, "window": "24h"})
	})

	stack := middleware.RateLimiter(100, 200)(middleware.TenantAuth(apiKeys)(r))

	server := &http.Server{Addr: ":8080", Handler: stack}
	log.Println("cloud gateway listening on :8080")
	log.Fatal(server.ListenAndServe())
}
