//! In-memory registry of provider trait objects behind interior mutability.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use crate::provider::Provider;

/// Holds the set of registered providers as `Arc<dyn Provider>`.
///
/// Providers are wrapped in `Arc` so the manager can hand out a cheap,
/// cloneable handle and then `await` async trait methods *without* holding the
/// registry lock across the await point. `Send + Sync` for the Tauri state.
pub struct ProviderRegistry {
    providers: Mutex<HashMap<String, Arc<dyn Provider>>>,
    /// Insertion order of ids, so listing/iteration is deterministic.
    order: Mutex<Vec<String>>,
}

impl Clone for ProviderRegistry {
    fn clone(&self) -> Self {
        let providers = self.providers.lock().expect("registry lock poisoned");
        let order = self.order.lock().expect("order lock poisoned");
        Self {
            providers: Mutex::new(providers.clone()),
            order: Mutex::new(order.clone()),
        }
    }
}

impl Default for ProviderRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl ProviderRegistry {
    pub fn new() -> Self {
        Self {
            providers: Mutex::new(HashMap::new()),
            order: Mutex::new(Vec::new()),
        }
    }

    /// Insert or replace a provider, keyed by its `id`. Preserves insertion
    /// order: a newly inserted id is appended; a re-inserted id keeps its slot.
    pub fn register(&self, provider: Arc<dyn Provider>) {
        let id = provider.id().to_string();
        self.providers
            .lock()
            .expect("registry lock poisoned")
            .insert(id.clone(), provider);
        let mut order = self.order.lock().expect("order lock poisoned");
        if !order.contains(&id) {
            order.push(id);
        }
    }

    /// Remove a provider by id. Returns true if one was removed.
    pub fn unregister(&self, id: &str) -> bool {
        let removed = self
            .providers
            .lock()
            .expect("registry lock poisoned")
            .remove(id)
            .is_some();
        if removed {
            let mut order = self.order.lock().expect("order lock poisoned");
            order.retain(|k| k != id);
        }
        removed
    }

    /// Borrow a provider by id, returning a cloneable handle.
    pub fn get(&self, id: &str) -> Option<Arc<dyn Provider>> {
        self.providers
            .lock()
            .expect("registry lock poisoned")
            .get(id)
            .cloned()
    }

    /// Snapshot of all provider ids in registration (insertion) order.
    pub fn ids(&self) -> Vec<String> {
        self.order.lock().expect("order lock poisoned").clone()
    }

    /// Number of registered providers.
    pub fn len(&self) -> usize {
        self.providers.lock().expect("registry lock poisoned").len()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Call `f` once per provider in registration (insertion) order.
    pub fn for_each<F: FnMut(&dyn Provider)>(&self, mut f: F) {
        let order = self.order.lock().expect("order lock poisoned");
        let providers = self.providers.lock().expect("registry lock poisoned");
        for id in order.iter() {
            if let Some(p) = providers.get(id) {
                f(p.as_ref());
            }
        }
    }

    /// All providers as a vector of handles, in registration order.
    pub fn all(&self) -> Vec<Arc<dyn Provider>> {
        let order = self.order.lock().expect("order lock poisoned");
        let providers = self.providers.lock().expect("registry lock poisoned");
        order
            .iter()
            .filter_map(|id| providers.get(id).cloned())
            .collect()
    }
}
