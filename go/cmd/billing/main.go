// P8 Cloud Platform — billing metering service (Go, separate process).
//
// Ingests usage events, aggregates them into per-tenant invoices, and
// exposes a query endpoint. The Python enterprise.cloud service mirrors
// the same logic into the SQL ``usage_events`` / ``invoices`` tables.
//
// Build/run (where Go is installed):
//   go run ./cmd/billing
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"
)

type UsageEvent struct {
	TenantID string  `json:"tenant_id"`
	Metric   string  `json:"metric"`
	Quantity float64 `json:"quantity"`
	UnitPrice float64 `json:"unit_price"`
}

type Billing struct {
	mu      sync.Mutex
	events  []UsageEvent
	byTenant map[string][]UsageEvent
}

func NewBilling() *Billing {
	return &Billing{byTenant: map[string][]UsageEvent{}}
}

func (b *Billing) ingest(w http.ResponseWriter, r *http.Request) {
	var e UsageEvent
	if err := json.NewDecoder(r.Body).Decode(&e); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	b.mu.Lock()
	b.events = append(b.events, e)
	b.byTenant[e.TenantID] = append(b.byTenant[e.TenantID], e)
	b.mu.Unlock()
	w.WriteHeader(http.StatusCreated)
}

// invoice computes the total for a tenant; discrepancy vs a stored invoice
// must be within the P8 KPI (<= 0.5%).
func (b *Billing) invoice(w http.ResponseWriter, r *http.Request) {
	tenant := r.URL.Query().Get("tenant")
	b.mu.Lock()
	defer b.mu.Unlock()
	var total float64
	for _, e := range b.byTenant[tenant] {
		total += e.Quantity * e.UnitPrice
	}
	json.NewEncoder(w).Encode(map[string]any{"tenant": tenant, "total": round2(total)})
}

func round2(v float64) float64 {
	return float64(int64(v*100+0.5)) / 100
}

func main() {
	b := NewBilling()
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("ok")) })
	mux.HandleFunc("/usage", b.ingest)
	mux.HandleFunc("/invoice", b.invoice)
	log.Println("billing metering listening on :8081")
	log.Fatal(http.ListenAndServe(":8081", mux))
}
