package main

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"
)

var (
	tenants = map[string]string{
		"demo-key": "tenant-demo",
	}
	passkeys = map[string]string{}
	mu       sync.Mutex
)

func main() {
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
		mu.Lock()
		passkeys[base64.RawURLEncoding.EncodeToString(challenge)] = tenantID
		mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"challenge":"%s","rp":{"name":"Prometheus"}}`, base64.RawURLEncoding.EncodeToString(challenge))
	})

	r.HandleFunc("/v1/auth/passkey/verify", func(w http.ResponseWriter, r *http.Request) {
		apiKey := generateAPIKey()
		mu.Lock()
		tenants[apiKey] = "tenant-" + time.Now().Format("20060102150405")
		mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"api_key":"%s","tenant_id":"%s"}`, apiKey, tenants[apiKey])
	})

	r.HandleFunc("/v1/tenants", func(w http.ResponseWriter, r *http.Request) {
		list := make([]map[string]string, 0)
		for k, v := range tenants {
			list = append(list, map[string]string{"api_key": k, "tenant_id": v})
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"tenants": list})
	})

	server := &http.Server{Addr: ":8081", Handler: r}
	fmt.Println("auth service listening on :8081")
	log.Fatal(server.ListenAndServe())
}

func generateAPIKey() string {
	buf := make([]byte, 32)
	rand.Read(buf)
	return base64.RawURLEncoding.EncodeToString(buf)
}
