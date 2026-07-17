package middleware

import (
	"context"
	"net/http"
	"strings"
)

type contextKey string

const TenantIDKey contextKey = "tenant_id"

func TenantAuth(apiKeys map[string]string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			h := r.Header.Get("Authorization")
			if !strings.HasPrefix(h, "Bearer ") {
				w.WriteHeader(http.StatusUnauthorized)
				return
			}
			key := strings.TrimPrefix(h, "Bearer ")
			tenantID, ok := apiKeys[key]
			if !ok {
				w.WriteHeader(http.StatusUnauthorized)
				return
			}
			ctx := context.WithValue(r.Context(), TenantIDKey, tenantID)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func TenantIDFromContext(ctx context.Context) (string, bool) {
	v, ok := ctx.Value(TenantIDKey).(string)
	return v, ok
}
