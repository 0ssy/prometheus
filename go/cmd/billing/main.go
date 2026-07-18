// P8 Cloud Platform — billing metering service (Go, separate process).
//
// Ingests usage events, aggregates them into per-tenant invoices, and
// exposes a query endpoint. The Python enterprise.cloud service mirrors
// the same logic into the SQL ``usage_events`` / ``invoices`` tables.
//
// Usage events are now persisted to BoltDB (loaded on startup) and invoice
// totals are recomputed from the durable stream, satisfying the P8
// "persistent rather than in-memory" Definition of Done.
//
// Build/run (where Go is installed):
//   go run ./cmd/billing
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"prometheus/internal/persistence"
)

const dbPath = "billing.db"

type UsageEvent struct {
	TenantID  string  `json:"tenant_id"`
	Metric    string  `json:"metric"`
	Quantity  float64 `json:"quantity"`
	UnitPrice float64 `json:"unit_price"`
}

type Billing struct {
	mu     sync.Mutex
	store  *persistence.Store
	events []UsageEvent
}

func NewBilling(store *persistence.Store) *Billing {
	b := &Billing{store: store}
	loaded, err := store.ListBillingEvents()
	if err != nil {
		log.Printf("load billing events: %v", err)
		return b
	}
	for _, e := range loaded {
		b.events = append(b.events, UsageEvent{
			TenantID:  e.TenantID,
			Metric:    e.Metric,
			Quantity:  e.Quantity,
			UnitPrice: e.UnitPrice,
		})
	}
	log.Printf("loaded %d usage events from BoltDB", len(b.events))
	return b
}

func (b *Billing) ingest(w http.ResponseWriter, r *http.Request) {
	var e UsageEvent
	if err := json.NewDecoder(r.Body).Decode(&e); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	if err := b.store.AppendBillingEvent(persistence.BillingEvent{
		TenantID:  e.TenantID,
		Metric:    e.Metric,
		Quantity:  e.Quantity,
		UnitPrice: e.UnitPrice,
	}); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	b.mu.Lock()
	b.events = append(b.events, e)
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
	for _, e := range b.events {
		if e.TenantID == tenant {
			total += e.Quantity * e.UnitPrice
		}
	}
	json.NewEncoder(w).Encode(map[string]any{"tenant": tenant, "total": round2(total)})
}

func round2(v float64) float64 {
	return float64(int64(v*100+0.5)) / 100
}

func main() {
	store, err := persistence.Open(dbPath)
	if err != nil {
		log.Fatalf("open persistence: %v", err)
	}
	defer store.Close()

	b := NewBilling(store)

	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("ok")) })
	mux.HandleFunc("/usage", b.ingest)
	mux.HandleFunc("/invoice", b.invoice)

	srv := &http.Server{Addr: ":8081", Handler: mux}
	go func() {
		log.Println("billing metering listening on :8081")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf("http serve: %v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGINT, syscall.SIGTERM)
	<-stop
	log.Println("shutting down; saving state...")
	if err := srv.Close(); err != nil {
		log.Printf("http close: %v", err)
	}
	if err := store.Close(); err != nil {
		log.Printf("persistence close: %v", err)
	}
	log.Println("state saved; bye")
}
