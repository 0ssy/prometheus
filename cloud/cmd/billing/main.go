package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/prometheus-eng/cloud/internal/billing"
	"github.com/prometheus-eng/cloud/internal/tenant"
)

var meter *billing.Meter
var store = map[string]*tenant.Tenant{}
var mu sync.Mutex

func init() {
	meter = billing.NewMeter(30 * 24 * time.Hour)
	store["tenant-demo"] = &tenant.Tenant{ID: "tenant-demo", Name: "Demo Org", Created: time.Now().Unix()}
}

func main() {
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
	fmt.Println("billing service listening on :8082")
	log.Fatal(server.ListenAndServe())
}
