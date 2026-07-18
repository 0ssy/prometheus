// P8 Cloud Platform — shared BoltDB persistence helper.
//
// Provides a small concurrency-safe wrapper around a single *bbolt.DB for
// the cloud services (gateway, billing, auth, tunnel). Each service keeps
// its own database file; buckets are created on open so callers can rely
// on persistence immediately after NewStore.
package store

import (
	"encoding/json"
	"errors"
	"sync"
	"time"

	bolt "go.etcd.io/bbolt"
)

// Store wraps a *bbolt.DB.
type Store struct {
	db   *bolt.DB
	mu   sync.Mutex // serializes read-modify-write sequences
	path string
}

// NewStore opens (or creates) the BoltDB file at path and ensures the
// given buckets exist.
func NewStore(path string, buckets ...[]byte) (*Store, error) {
	if path == "" {
		return nil, errors.New("store: path required")
	}
	db, err := bolt.Open(path, 0o600, &bolt.Options{Timeout: 5 * time.Second})
	if err != nil {
		return nil, err
	}
	s := &Store{db: db, path: path}
	if err := s.db.Update(func(tx *bolt.Tx) error {
		for _, b := range buckets {
			if _, err := tx.CreateBucketIfNotExists(b); err != nil {
				return err
			}
		}
		return nil
	}); err != nil {
		_ = db.Close()
		return nil, err
	}
	return s, nil
}

// Path returns the database file path.
func (s *Store) Path() string { return s.path }

// DB exposes the underlying database for advanced callers.
func (s *Store) DB() *bolt.DB { return s.db }

// Close flushes and closes the underlying database.
func (s *Store) Close() error {
	if s.db == nil {
		return nil
	}
	return s.db.Close()
}

// PutJSON marshals v and stores it under key in bucket.
func (s *Store) PutJSON(bucket, key []byte, v any) error {
	data, err := json.Marshal(v)
	if err != nil {
		return err
	}
	return s.db.Update(func(tx *bolt.Tx) error {
		return tx.Bucket(bucket).Put(key, data)
	})
}

// GetJSON loads the value stored under key into out. It returns (false, nil)
// when the key is absent.
func (s *Store) GetJSON(bucket, key []byte, out any) (bool, error) {
	found := false
	err := s.db.View(func(tx *bolt.Tx) error {
		v := tx.Bucket(bucket).Get(key)
		if v == nil {
			return nil
		}
		found = true
		return json.Unmarshal(v, out)
	})
	return found, err
}

// Delete removes key from bucket.
func (s *Store) Delete(bucket, key []byte) error {
	return s.db.Update(func(tx *bolt.Tx) error {
		return tx.Bucket(bucket).Delete(key)
	})
}

// ForEach iterates every key/value pair in bucket, decoding JSON into out
// via fn. Iteration stops on the first error returned by fn.
func (s *Store) ForEach(bucket []byte, fn func(key []byte, value json.RawMessage) error) error {
	return s.db.View(func(tx *bolt.Tx) error {
		return tx.Bucket(bucket).ForEach(func(k, v []byte) error {
			return fn(k, v)
		})
	})
}

// AppendJSON appends a value under a sequence-keyed bucket. The key is
// "seq:<n>" so entries are never overwritten. Returns the assigned key.
func (s *Store) AppendJSON(bucket []byte, v any) ([]byte, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	data, err := json.Marshal(v)
	if err != nil {
		return nil, err
	}
	var n int
	if err := s.db.View(func(tx *bolt.Tx) error {
		n = tx.Bucket(bucket).Stats().KeyN
		return nil
	}); err != nil {
		return nil, err
	}
	key := []byte("seq:" + itoa(n))
	err = s.db.Update(func(tx *bolt.Tx) error {
		return tx.Bucket(bucket).Put(key, data)
	})
	if err != nil {
		return nil, err
	}
	return key, nil
}

func itoa(v int) string {
	if v == 0 {
		return "0"
	}
	var b [12]byte
	i := len(b)
	for v > 0 {
		i--
		b[i] = byte('0' + v%10)
		v /= 10
	}
	return string(b[i:])
}
