package main

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/prometheus-eng/cloud/internal/store"
)

var (
	bucketTenants    = []byte("tenants")
	bucketChallenges = []byte("passkey_challenges")
)

var (
	apiKeysMu sync.Mutex
	tenants   = map[string]string{} // apiKey -> tenantID
	passkeys  = map[string]string{} // challenge -> tenantID
	storeDB   *store.Store
)

func main() {
	db, err := store.NewStore("auth.db", bucketTenants, bucketChallenges)
	if err != nil {
		log.Fatalf("open persistence: %v", err)
	}
	storeDB = db
	defer db.Close()

	loadState()

	r := http.NewServeMux()
	r.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, `{"status":"ok"}`)
	})

	r.HandleFunc("/v1/auth/oidc/login", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, `{"auth_url":"https://idp.example.com/auth?client_id=prometheus"}`)
	})

	r.HandleFunc("/v1/auth/passkey/register", func(w http.ResponseWriter, r *http.Request) {
		tenantID := r.URL.Query().Get("tenant_id")
		challenge := make([]byte, 32)
		rand.Read(challenge)
		challengeStr := base64.RawURLEncoding.EncodeToString(challenge)
		apiKeysMu.Lock()
		passkeys[challengeStr] = tenantID
		apiKeysMu.Unlock()
		if err := storeDB.PutJSON(bucketChallenges, []byte(challengeStr), map[string]string{"tenant_id": tenantID}); err != nil {
			log.Printf("persist challenge: %v", err)
		}
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"challenge":"%s","rp":{"name":"Prometheus"}}`, challengeStr)
	})

	r.HandleFunc("/v1/auth/passkey/verify", func(w http.ResponseWriter, r *http.Request) {
		apiKey := generateAPIKey()
		tenantID := "tenant-" + time.Now().Format("20060102150405")
		apiKeysMu.Lock()
		tenants[apiKey] = tenantID
		apiKeysMu.Unlock()
		if err := storeDB.PutJSON(bucketTenants, []byte(apiKey), map[string]string{"tenant_id": tenantID}); err != nil {
			log.Printf("persist tenant: %v", err)
		}
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"api_key":"%s","tenant_id":"%s"}`, apiKey, tenantID)
	})

	r.HandleFunc("/v1/tenants", func(w http.ResponseWriter, r *http.Request) {
		list := make([]map[string]string, 0)
		apiKeysMu.Lock()
		for k, v := range tenants {
			list = append(list, map[string]string{"api_key": k, "tenant_id": v})
		}
		apiKeysMu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"tenants": list})
	})

	server := &http.Server{Addr: ":8081", Handler: r}
	go func() {
		fmt.Println("auth service listening on :8081")
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

func loadState() {
	apiKeysMu.Lock()
	defer apiKeysMu.Unlock()
	_ = storeDB.ForEach(bucketTenants, func(key []byte, value json.RawMessage) error {
		var m map[string]string
		if err := json.Unmarshal(value, &m); err != nil {
			return nil
		}
		tenants[string(key)] = m["tenant_id"]
		return nil
	})
	_ = storeDB.ForEach(bucketChallenges, func(key []byte, value json.RawMessage) error {
		var m map[string]string
		if err := json.Unmarshal(value, &m); err != nil {
			return nil
		}
		passkeys[string(key)] = m["tenant_id"]
		return nil
	})
	if len(tenants) == 0 {
		tenants["demo-key"] = "tenant-demo"
		_ = storeDB.PutJSON(bucketTenants, []byte("demo-key"), map[string]string{"tenant_id": "tenant-demo"})
	}
	log.Printf("loaded %d tenants, %d passkey challenges from BoltDB", len(tenants), len(passkeys))
}

func generateAPIKey() string {
	buf := make([]byte, 32)
	rand.Read(buf)
	return base64.RawURLEncoding.EncodeToString(buf)
}
