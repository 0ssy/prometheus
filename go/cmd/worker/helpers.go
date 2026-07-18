package main

import (
	"net"
	"os"
)

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func net_join(host, port string) string {
	return net.JoinHostPort(host, port)
}

func readKeyFile(path string) ([]byte, error) {
	return os.ReadFile(path)
}
