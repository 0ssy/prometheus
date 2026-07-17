package middleware

import (
	"net/http"
	"strings"
	"sync"
	"time"
)

func RateLimiter(rps int, burst int) func(http.Handler) http.Handler {
	type token struct{ t time.Time }
	var mu sync.Mutex
	buckets := make(map[string][]token)

	cleanup := time.NewTicker(time.Minute)
	go func() {
		for range cleanup.C {
			mu.Lock()
			for ip, toks := range buckets {
				kept := make([]token, 0)
				for _, t := range toks {
					if time.Since(t.t) < time.Minute {
						kept = append(kept, t)
					}
				}
				if len(kept) == 0 {
					delete(buckets, ip)
				} else {
					buckets[ip] = kept
				}
			}
			mu.Unlock()
		}
	}()

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			ip := strings.Split(r.RemoteAddr, ":")[0]
			mu.Lock()
			var toks []token
			for _, t := range buckets[ip] {
				if time.Since(t.t) < time.Minute {
					toks = append(toks, t)
				}
			}
			if len(toks) >= burst {
				mu.Unlock()
				w.WriteHeader(http.StatusTooManyRequests)
				return
			}
			toks = append(toks, token{t: time.Now()})
			buckets[ip] = toks
			mu.Unlock()
			next.ServeHTTP(w, r)
		})
	}
}
