// P7 Distributed Computing — mDNS peer discovery (stdlib only).
//
// Implements the mDNS wire protocol (RFC 6762) over UDP multicast on the
// standard link-local addresses 224.0.0.251:5353 (IPv4) and FF02::FB:5353
// (IPv6). This replaces the previous JSON-datagram hack, which was not
// valid DNS wire format and was rejected by conformant mDNS responders.
//
// We announce a single PTR/SRV/TXT/A record set advertising this node's
// role and reachable address, and listen for the same records from peers.
// The control plane uses the peer list to seed its bootstrap; workers use
// it to locate a control plane without a hardcoded address.
//
// The implementation is intentionally minimal: it does NOT implement the
// full cache-flush / known-answer / probing state machine, but it speaks
// real DNS message format so other mDNS stacks can interoperate.
package mdns

import (
	"encoding/binary"
	"log"
	"net"
	"strings"
	"sync"
	"time"
)

const (
	mdnsAddr4   = "224.0.0.251"
	mdnsAddr6   = "ff02::fb"
	mdnsPort    = 5353
	serviceName = "_prometheus._tcp.local."
	announceEvery = 5 * time.Second
	peerTTL       = 15 * time.Second
)

// Announce describes a discovered/local node.
type Announce struct {
	ID   string `json:"id"`
	Role string `json:"role"` // "controlplane" | "worker"
	Addr string `json:"addr"` // reachable unicast address
}

// Discovery manages announcement and peer tracking.
type Discovery struct {
	self    Announce
	iface   *net.Interface
	mu      sync.Mutex
	peers   map[string]peerEntry
	conns   []*net.UDPConn
	closed  bool
	closeCh chan struct{}
}

type peerEntry struct {
	ann  Announce
	seen time.Time
}

// New starts discovery for a node with the given id/role/addr.
func New(id, role, addr string) *Discovery {
	return &Discovery{
		self:    Announce{ID: id, Role: role, Addr: addr},
		peers:   map[string]peerEntry{},
		closeCh: make(chan struct{}),
	}
}

// Start joins the multicast groups, begins announcing and listening.
func (d *Discovery) Start() error {
	joined := false
	for _, a := range []string{mdnsAddr4, mdnsAddr6} {
		conn, err := d.listenGroup(a)
		if err != nil {
			log.Printf("mdns join %s: %v", a, err)
			continue
		}
		d.conns = append(d.conns, conn)
		joined = true
	}
	if !joined {
		return net.UnknownNetworkError("mdns: could not listen on any multicast group")
	}
	go d.announceLoop()
	for _, c := range d.conns {
		go d.listenLoop(c)
	}
	return nil
}

// listenGroup opens a UDP multicast socket bound to the mDNS port on the
// given multicast address. net.ListenMulticastUDP joins the group and is
// the stdlib-sanctioned way to subscribe to 224.0.0.251 / FF02::FB.
func (d *Discovery) listenGroup(addr string) (*net.UDPConn, error) {
	ua, err := net.ResolveUDPAddr("udp", net.JoinHostPort(addr, itoa(mdnsPort)))
	if err != nil {
		return nil, err
	}
	network := "udp4"
	if ua.IP.To4() == nil {
		network = "udp6"
	}
	return net.ListenMulticastUDP(network, nil, ua)
}

// Stop terminates announcement and listening.
func (d *Discovery) Stop() {
	d.mu.Lock()
	if d.closed {
		d.mu.Unlock()
		return
	}
	d.closed = true
	close(d.closeCh)
	d.mu.Unlock()
	for _, c := range d.conns {
		_ = c.Close()
	}
}

func (d *Discovery) announceLoop() {
	ticker := time.NewTicker(announceEvery)
	defer ticker.Stop()
	d.send()
	for {
		select {
		case <-d.closeCh:
			return
		case <-ticker.C:
			d.send()
		}
	}
}

// send broadcasts the mDNS announcement on every joined socket.
func (d *Discovery) send() {
	msg := d.buildAnnounce()
	for _, c := range d.conns {
		var dst *net.UDPAddr
		if c.LocalAddr().(*net.UDPAddr).IP.To4() != nil {
			dst = &net.UDPAddr{IP: net.ParseIP(mdnsAddr4), Port: mdnsPort}
		} else {
			dst = &net.UDPAddr{IP: net.ParseIP(mdnsAddr6), Port: mdnsPort}
		}
		if _, err := c.WriteTo(msg, dst); err != nil {
			log.Printf("mdns announce: %v", err)
		}
	}
}

// buildAnnounce encodes an mDNS response (answer section) advertising this
// node. Records:
//   PTR _prometheus._tcp.local -> <id>._prometheus._tcp.local
//   SRV <id>._prometheus._tcp.local -> port/host
//   TXT <id>._prometheus._tcp.local -> role=<role>
//   A/AAAA addr (best-effort; skipped if addr is not an IP)
func (d *Discovery) buildAnnounce() []byte {
	instance := d.self.ID + "." + serviceName
	var buf []byte

	buf = appendDNSName(buf, serviceName)
	buf = appendUint16(buf, 12) // PTR
	buf = appendUint16(buf, 1)  // IN
	buf = appendUint32(buf, uint32(peerTTL.Seconds()))
	rdata := encodeName(instance)
	buf = appendUint16(buf, uint16(len(rdata)))
	buf = append(buf, rdata...)

	buf = appendDNSName(buf, instance)
	buf = appendUint16(buf, 33) // SRV
	buf = appendUint16(buf, 1)
	buf = appendUint32(buf, uint32(peerTTL.Seconds()))
	host := stripPort(d.self.Addr)
	srv := appendUint16(appendUint16([]byte{}, 0), 0) // priority, weight
	srv = appendUint16(srv, uint16(guessPort(d.self.Addr)))
	srv = append(srv, encodeName(host)...)
	buf = appendUint16(buf, uint16(len(srv)))
	buf = append(buf, srv...)

	buf = appendDNSName(buf, instance)
	buf = appendUint16(buf, 16) // TXT
	buf = appendUint16(buf, 1)
	buf = appendUint32(buf, uint32(peerTTL.Seconds()))
	txt := encodeText("role=" + d.self.Role)
	buf = appendUint16(buf, uint16(len(txt)))
	buf = append(buf, txt...)

	if ip := net.ParseIP(host); ip != nil {
		if ip.To4() != nil {
			buf = appendDNSName(buf, instance)
			buf = appendUint16(buf, 1) // A
			buf = appendUint16(buf, 1)
			buf = appendUint32(buf, uint32(peerTTL.Seconds()))
			buf = appendUint16(buf, 4)
			buf = append(buf, ip.To4()...)
		} else {
			buf = appendDNSName(buf, instance)
			buf = appendUint16(buf, 28) // AAAA
			buf = appendUint16(buf, 1)
			buf = appendUint32(buf, uint32(peerTTL.Seconds()))
			buf = appendUint16(buf, 16)
			buf = append(buf, ip.To16()...)
		}
	}

	return encodeDNSMessage(0, buf)
}

func (d *Discovery) listenLoop(c *net.UDPConn) {
	buf := make([]byte, 4096)
	for {
		select {
		case <-d.closeCh:
			return
		default:
		}
		_ = c.SetReadDeadline(time.Now().Add(announceEvery))
		n, src, err := c.ReadFrom(buf)
		if err != nil {
			if ne, ok := err.(net.Error); ok && ne.Timeout() {
				continue
			}
			select {
			case <-d.closeCh:
				return
			default:
			}
			continue
		}
		ann, ok := parseAnnounce(buf[:n])
		if !ok || ann.ID == d.self.ID {
			continue
		}
		_ = src
		d.mu.Lock()
		d.peers[ann.ID] = peerEntry{ann: ann, seen: time.Now()}
		d.mu.Unlock()
	}
}

// Peers returns the currently discovered peers.
func (d *Discovery) Peers() []Announce {
	d.mu.Lock()
	defer d.mu.Unlock()
	now := time.Now()
	out := make([]Announce, 0, len(d.peers))
	for id, p := range d.peers {
		if now.Sub(p.seen) > peerTTL {
			delete(d.peers, id)
			continue
		}
		out = append(out, p.ann)
	}
	return out
}

// ----------------------------------------------------- DNS wire helpers ---

func encodeDNSMessage(id uint16, answers []byte) []byte {
	// QR=1 (response), opcode=0, AA=1 (authoritative)
	flags := uint16(0x8400)
	hdr := make([]byte, 12)
	binary.BigEndian.PutUint16(hdr[0:], id)
	binary.BigEndian.PutUint16(hdr[2:], flags)
	binary.BigEndian.PutUint16(hdr[4:], 0) // qdcount
	binary.BigEndian.PutUint16(hdr[6:], uint16(countRecords(answers)))
	binary.BigEndian.PutUint16(hdr[8:], 0)  // nscount
	binary.BigEndian.PutUint16(hdr[10:], 0) // arcount
	return append(hdr, answers...)
}

// countRecords counts the number of resource records in a buffer that
// starts at record boundaries (name/type/class/ttl/rdlen/rdata ...).
func countRecords(b []byte) int {
	count := 0
	i := 0
	for i < len(b) {
		_, n := skipName(b, i)
		if n <= 0 {
			break
		}
		i = n + 10 // type(2)+class(2)+ttl(4)+rdlen(2)
		if i > len(b) {
			break
		}
		rdlen := int(binary.BigEndian.Uint16(b[i-2 : i]))
		i += rdlen
		count++
	}
	return count
}

func parseAnnounce(b []byte) (Announce, bool) {
	if len(b) < 12 {
		return Announce{}, false
	}
	ancount := int(binary.BigEndian.Uint16(b[6:8]))
	var ann Announce
	i := 12
	for r := 0; r < ancount && i < len(b); r++ {
		_, n := skipName(b, i)
		if n <= 0 {
			break
		}
		if i+10 > len(b) {
			break
		}
		rtype := binary.BigEndian.Uint16(b[n : n+2])
		rdlen := int(binary.BigEndian.Uint16(b[n+8 : n+10]))
		rdata := b[n+10 : n+10+rdlen]
		switch rtype {
		case 12: // PTR -> instance name
			instance, _ := readNameAt(b, int(binary.BigEndian.Uint16(rdata)))
			if id, ok := strings.CutSuffix(instance, "."+serviceName); ok {
				ann.ID = id
			}
		case 16: // TXT
			for off := 0; off < len(rdata); {
				l := int(rdata[off])
				off++
				if off+l > len(rdata) {
					break
				}
				kv := string(rdata[off : off+l])
				if v, ok := strings.CutPrefix(kv, "role="); ok {
					ann.Role = v
				}
				off += l
			}
		case 33: // SRV -> target host
			if len(rdata) >= 6 {
				target, _ := readNameAt(b, int(binary.BigEndian.Uint16(rdata[5:])))
				ann.Addr = target
			}
		}
		i = n + 10 + rdlen
	}
	if ann.ID == "" {
		return Announce{}, false
	}
	return ann, true
}

// encodeName writes a DNS-compressed-less name (sequence of labels).
func encodeName(name string) []byte {
	name = strings.TrimSuffix(name, ".")
	var out []byte
	for _, label := range strings.Split(name, ".") {
		out = append(out, byte(len(label)))
		out = append(out, []byte(label)...)
	}
	return append(out, 0)
}

func appendDNSName(buf []byte, name string) []byte {
	return append(buf, encodeName(name)...)
}

func appendUint16(b []byte, v uint16) []byte {
	return append(b, byte(v>>8), byte(v))
}

func appendUint32(b []byte, v uint32) []byte {
	return append(b, byte(v>>24), byte(v>>16), byte(v>>8), byte(v))
}

func encodeText(s string) []byte {
	b := []byte(s)
	out := append([]byte{byte(len(b))}, b...)
	return out
}

// skipName returns the name string starting at offset i and the offset just
// past it. It does not follow compression pointers (announcements we emit
// are uncompressed).
func skipName(b []byte, i int) (string, int) {
	var labels []string
	for i < len(b) {
		l := int(b[i])
		if l == 0 {
			i++
			break
		}
		if l&0xC0 == 0xC0 {
			i += 2
			break
		}
		i++
		if i+l > len(b) {
			return "", -1
		}
		labels = append(labels, string(b[i:i+l]))
		i += l
	}
	return strings.Join(labels, "."), i
}

// readNameAt reads an uncompressed name at offset i.
func readNameAt(b []byte, i int) (string, int) {
	return skipName(b, i)
}

func stripPort(addr string) string {
	if h, _, err := net.SplitHostPort(addr); err == nil {
		return h
	}
	return addr
}

func guessPort(addr string) int {
	if _, p, err := net.SplitHostPort(addr); err == nil && p != "" {
		n := 0
		for _, c := range p {
			if c < '0' || c > '9' {
				return 8080
			}
			n = n*10 + int(c-'0')
		}
		if n > 0 {
			return n
		}
	}
	return 8080
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
