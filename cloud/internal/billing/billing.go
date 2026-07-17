package billing

import (
	"sync"
	"time"
)

type UsageEvent struct {
	TenantID string
	Resource string
	Quantity float64
	Unit     string
	At       time.Time
}

type Meter struct {
	mu      sync.Mutex
	events  []UsageEvent
	window  time.Duration
}

func NewMeter(window time.Duration) *Meter {
	return &Meter{window: window}
}

func (m *Meter) Record(e UsageEvent) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.events = append(m.events, e)
}

func (m *Meter) Snapshot(tenantID string) map[string]float64 {
	m.mu.Lock()
	defer m.mu.Unlock()
	totals := make(map[string]float64)
	cutoff := time.Now().Add(-m.window)
	for _, e := range m.events {
		if e.TenantID == tenantID && e.At.After(cutoff) {
			totals[e.Resource] += e.Quantity
		}
	}
	return totals
}
