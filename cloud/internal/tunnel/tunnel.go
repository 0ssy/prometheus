package tunnel

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
	"net"
	"os"
	"sync"
	"time"

	"golang.org/x/crypto/ssh"
)

type Tunnel struct {
	ID          string
	LocalAddr   string
	RemoteAddr  string
	SSHAddr     string
	SSHUser     string
	SSHAuth     []ssh.AuthMethod
	CreatedAt   time.Time
	ClosedAt    *time.Time
	Listener    net.Listener
	ClientConn  *ssh.Client
}

type TunnelConfig struct {
	LocalPort   int
	RemoteAddr  string
	SSHAddr     string
	SSHUser     string
	SSHPassword string
	SSHKeyPath  string
}

type TunnelStatus struct {
	ID         string     `json:"id"`
	LocalAddr  string     `json:"local_addr"`
	RemoteAddr string     `json:"remote_addr"`
	SSHAddr    string     `json:"ssh_addr"`
	SSHUser    string     `json:"ssh_user"`
	CreatedAt  time.Time  `json:"created_at"`
	ClosedAt   *time.Time `json:"closed_at,omitempty"`
	Active     bool       `json:"active"`
}

var (
	mu       sync.Mutex
	tunnels  = map[string]*Tunnel{}
	nextPort = 10000
)

func generateTunnelID() string {
	buf := make([]byte, 16)
	rand.Read(buf)
	return hex.EncodeToString(buf)
}

func nextAvailablePort() int {
	mu.Lock()
	defer mu.Unlock()
	for {
		p := nextPort
		nextPort++
		if ln, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", p)); err == nil {
			ln.Close()
			return p
		}
	}
}

func buildSSHClient(cfg TunnelConfig) (*ssh.Client, error) {
	auth := make([]ssh.AuthMethod, 0)
	if cfg.SSHPassword != "" {
		auth = append(auth, ssh.Password(cfg.SSHPassword))
	}
	if cfg.SSHKeyPath != "" {
		key, err := os.ReadFile(cfg.SSHKeyPath)
		if err != nil {
			return nil, fmt.Errorf("read ssh key: %w", err)
		}
		signer, err := ssh.ParsePrivateKey(key)
		if err != nil {
			return nil, fmt.Errorf("parse ssh key: %w", err)
		}
		auth = append(auth, ssh.PublicKeys(signer))
	}
	if len(auth) == 0 {
		return nil, fmt.Errorf("no ssh auth method provided")
	}

	sshCfg := &ssh.ClientConfig{
		User:            cfg.SSHUser,
		Auth:            auth,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
		Timeout:         10 * time.Second,
	}
	return ssh.Dial("tcp", cfg.SSHAddr, sshCfg)
}

func forwardPort(conn net.Conn, remoteAddr string, client *ssh.Client) {
	defer conn.Close()
	rconn, err := client.Dial("tcp", remoteAddr)
	if err != nil {
		return
	}
	defer rconn.Close()
	done := make(chan struct{}, 2)
	go func() {
		io.Copy(rconn, conn)
		done <- struct{}{}
	}()
	go func() {
		io.Copy(conn, rconn)
		done <- struct{}{}
	}()
	<-done
}

func CreateTunnel(cfg TunnelConfig) (*Tunnel, error) {
	port := nextAvailablePort()
	localAddr := fmt.Sprintf("127.0.0.1:%d", port)
	client, err := buildSSHClient(cfg)
	if err != nil {
		return nil, fmt.Errorf("ssh connect failed: %w", err)
	}

	ln, err := net.Listen("tcp", localAddr)
	if err != nil {
		client.Close()
		return nil, fmt.Errorf("local listen failed: %w", err)
	}

	id := generateTunnelID()
	t := &Tunnel{
		ID:         id,
		LocalAddr:  localAddr,
		RemoteAddr: cfg.RemoteAddr,
		SSHAddr:    cfg.SSHAddr,
		SSHUser:    cfg.SSHUser,
		SSHAuth:    nil,
		CreatedAt:  time.Now(),
		Listener:   ln,
		ClientConn: client,
	}

	mu.Lock()
	tunnels[id] = t
	mu.Unlock()

	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			go forwardPort(conn, cfg.RemoteAddr, client)
		}
	}()

	return t, nil
}

func (t *Tunnel) Close() error {
	if t == nil {
		return nil
	}
	now := time.Now()
	t.ClosedAt = &now
	if t.Listener != nil {
		t.Listener.Close()
	}
	if t.ClientConn != nil {
		t.ClientConn.Close()
	}
	return nil
}

func ListActiveTunnels() []TunnelStatus {
	mu.Lock()
	defer mu.Unlock()
	out := make([]TunnelStatus, 0, len(tunnels))
	for _, t := range tunnels {
		out = append(out, TunnelStatus{
			ID:         t.ID,
			LocalAddr:  t.LocalAddr,
			RemoteAddr: t.RemoteAddr,
			SSHAddr:    t.SSHAddr,
			SSHUser:    t.SSHUser,
			CreatedAt:  t.CreatedAt,
			ClosedAt:   t.ClosedAt,
			Active:     t.ClosedAt == nil,
		})
	}
	return out
}

func GetTunnel(id string) (*Tunnel, bool) {
	mu.Lock()
	defer mu.Unlock()
	t, ok := tunnels[id]
	return t, ok
}
