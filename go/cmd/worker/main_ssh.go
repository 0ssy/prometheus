// P7 Distributed Computing — SSH-based task execution (Go, separate process).
//
// Alternative worker runtime that executes claimed task payloads as commands
// on a remote host over SSH (golang.org/x/crypto/ssh) instead of running them
// locally. The registration/polling protocol against the control plane is the
// same as cmd/worker/main.go; this file only replaces the local executor with
// an SSH session.
//
// Build/run (where Go is installed):
//   go run ./cmd/worker -ssh
//
// Connection parameters are read from the environment (SSH_HOST, SSH_PORT,
// SSH_USER, SSH_PASSWORD) or from an unencrypted private key file (SSH_KEY).
package main

import (
	"bytes"
	"fmt"
	"time"

	"golang.org/x/crypto/ssh"
)

type sshExecutor struct {
	client *ssh.Client
}

func newSSHExecutor() (*sshExecutor, error) {
	host := getenv("SSH_HOST", "localhost")
	port := getenv("SSH_PORT", "22")
	user := getenv("SSH_USER", "prometheus")
	password := getenv("SSH_PASSWORD", "")
	keyPath := getenv("SSH_KEY", "")

	var authMethods []ssh.AuthMethod
	if password != "" {
		authMethods = append(authMethods, ssh.Password(password))
	}
	if keyPath != "" {
		key, err := readKeyFile(keyPath)
		if err != nil {
			return nil, err
		}
		signer, err := ssh.ParsePrivateKey(key)
		if err != nil {
			return nil, fmt.Errorf("parse key: %w", err)
		}
		authMethods = append(authMethods, ssh.PublicKeys(signer))
	}
	if len(authMethods) == 0 {
		return nil, fmt.Errorf("no SSH auth method configured (set SSH_PASSWORD or SSH_KEY)")
	}

	cfg := &ssh.ClientConfig{
		User:            user,
		Auth:            authMethods,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(), // demo only; pin keys in prod
		Timeout:         10 * time.Second,
	}

	client, err := ssh.Dial("tcp", net_join(host, port), cfg)
	if err != nil {
		return nil, fmt.Errorf("ssh dial: %w", err)
	}
	return &sshExecutor{client: client}, nil
}

// run executes the given command on the remote host and returns its combined
// output. The task payload is treated as the command line.
func (e *sshExecutor) run(command string) (string, error) {
	session, err := e.client.NewSession()
	if err != nil {
		return "", err
	}
	defer session.Close()
	var out bytes.Buffer
	session.Stdout = &out
	session.Stderr = &out
	if err := session.Run(command); err != nil {
		return out.String(), fmt.Errorf("ssh run: %w", err)
	}
	return out.String(), nil
}

func (e *sshExecutor) close() error {
	return e.client.Close()
}
