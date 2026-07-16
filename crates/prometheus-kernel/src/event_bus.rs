use std::sync::{Arc, Mutex};

/// A kernel event that can be fanned out to webview listeners (Tauri events)
/// or to other Rust subscribers. Small, serializable payloads only.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct KernelEvent {
    /// Topic, e.g. `terminal-output`, `terminal-exited`, `session-restored`.
    pub topic: String,
    /// Optional target id (session id, window id, ...).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<String>,
    /// Arbitrary JSON payload.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub payload: Option<serde_json::Value>,
}

type Listener = Arc<dyn Fn(&KernelEvent) + Send + Sync + 'static>;

/// In-process publish/subscribe bus. The Tauri layer subscribes a single
/// forwarder that calls `app.emit(topic, payload)` so every event reaches the
/// webview without bespoke plumbing.
///
/// Lock scope is narrow: publish clones the listener list out of the lock,
/// then invokes callbacks without holding it, so a slow listener cannot block
/// publishers.
pub struct EventBus {
    listeners: Arc<Mutex<Vec<Listener>>>,
}

impl Clone for EventBus {
    fn clone(&self) -> Self {
        Self {
            listeners: Arc::clone(&self.listeners),
        }
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self {
            listeners: Arc::new(Mutex::new(Vec::new())),
        }
    }
}

impl EventBus {
    pub fn new() -> Self {
        Self::default()
    }

    /// Subscribe to every event. Returns a generation token used by
    /// `unsubscribe`.
    pub fn subscribe<F>(&self, listener: F) -> usize
    where
        F: Fn(&KernelEvent) + Send + Sync + 'static,
    {
        let mut guard = self.listeners.lock().unwrap();
        guard.push(Arc::new(listener));
        guard.len()
    }

    /// Remove the listener at the index returned by `subscribe`. No-op if the
    /// index is out of range (e.g. already removed).
    pub fn unsubscribe(&self, token: usize) {
        let mut guard = self.listeners.lock().unwrap();
        if token > 0 && token <= guard.len() {
            guard.remove(token - 1);
        }
    }

    /// Publish an event to all current listeners.
    pub fn publish(&self, event: KernelEvent) {
        let listeners: Vec<Listener> = {
            let guard = self.listeners.lock().unwrap();
            guard.clone()
        };
        for listener in listeners {
            listener(&event);
        }
    }

    /// Shared handle for the Tauri layer.
    pub fn shared() -> Arc<EventBus> {
        Arc::new(EventBus::new())
    }
}

pub type SharedEventBus = Arc<EventBus>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn publish_fans_out_to_all_listeners() {
        let bus = EventBus::new();
        let counter = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let c2 = counter.clone();
        bus.subscribe(move |_e| {
            c2.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        });
        let c3 = counter.clone();
        bus.subscribe(move |_e| {
            c3.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        });

        bus.publish(KernelEvent {
            topic: "ping".into(),
            target: None,
            payload: None,
        });

        assert_eq!(counter.load(std::sync::atomic::Ordering::SeqCst), 2);
    }

    #[test]
    fn unsubscribe_removes_listener() {
        let bus = EventBus::new();
        let counter = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let c2 = counter.clone();
        let token = bus.subscribe(move |_e| {
            c2.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        });
        bus.publish(KernelEvent {
            topic: "a".into(),
            target: None,
            payload: None,
        });
        bus.unsubscribe(token);
        bus.publish(KernelEvent {
            topic: "b".into(),
            target: None,
            payload: None,
        });
        assert_eq!(counter.load(std::sync::atomic::Ordering::SeqCst), 1);
    }

    #[test]
    fn payload_round_trips_through_serde() {
        let ev = KernelEvent {
            topic: "terminal-output".into(),
            target: Some("sess-1".into()),
            payload: Some(serde_json::json!({ "data": "aGVsbG8=" })),
        };
        let s = serde_json::to_string(&ev).unwrap();
        let back: KernelEvent = serde_json::from_str(&s).unwrap();
        assert_eq!(back.topic, "terminal-output");
        assert_eq!(back.target.as_deref(), Some("sess-1"));
    }
}
