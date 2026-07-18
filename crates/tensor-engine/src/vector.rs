//! P6 Vector Search — HNSW index and Qdrant integration.
//!
//! Provides:
//! - `HnswIndex`: in-memory approximate nearest neighbor search
//! - `QdrantClient`: HTTP client for distributed Qdrant mode

use std::cmp::Ordering;
use std::cmp::Reverse;
use std::collections::BinaryHeap;

#[cfg(feature = "qdrant")]
use anyhow::Context;

/// Configuration for HNSW index construction.
#[derive(Debug, Clone)]
pub struct HnswConfig {
    pub dim: usize,
    pub max_elements: usize,
    pub m: usize,
    pub ef_construction: usize,
    pub ef_search: usize,
    pub ml: f32,
}

impl Default for HnswConfig {
    fn default() -> Self {
        Self {
            dim: 768,
            max_elements: 10000,
            m: 16,
            ef_construction: 100,
            ef_search: 50,
            ml: 16.0_f32.ln().recip(),
        }
    }
}

/// Distance metric for vector comparison.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum DistanceMetric {
    #[default]
    Cosine,
    Euclidean,
    DotProduct,
}

impl DistanceMetric {
    pub fn distance(&self, a: &[f32], b: &[f32]) -> f32 {
        match self {
            DistanceMetric::Cosine => {
                let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
                let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
                let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
                if norm_a == 0.0 || norm_b == 0.0 {
                    1.0
                } else {
                    1.0 - dot / (norm_a * norm_b)
                }
            }
            DistanceMetric::Euclidean => {
                a.iter().zip(b.iter()).map(|(x, y)| (x - y).powi(2)).sum::<f32>().sqrt()
            }
            DistanceMetric::DotProduct => {
                -a.iter().zip(b.iter()).map(|(x, y)| x * y).sum::<f32>()
            }
        }
    }
}

/// A node in the HNSW graph.
#[derive(Debug, Clone)]
struct HnswNode {
    id: usize,
    vector: Vec<f32>,
    connections: Vec<Vec<usize>>,
    level: usize,
}

/// HNSW approximate nearest neighbor index.
#[derive(Debug, Default)]
pub struct HnswIndex {
    config: HnswConfig,
    nodes: Vec<HnswNode>,
    entry_point: Option<usize>,
    max_level: usize,
    metric: DistanceMetric,
}

impl HnswIndex {
    pub fn new(config: HnswConfig, metric: DistanceMetric) -> Self {
        Self {
            config,
            nodes: Vec::new(),
            entry_point: None,
            max_level: 0,
            metric,
        }
    }

    /// Insert a vector into the index.
    pub fn insert(&mut self, id: usize, vector: Vec<f32>) {
        assert_eq!(vector.len(), self.config.dim, "vector dimension mismatch");
        let level = self.random_level();
        let mut connections = vec![Vec::new(); level + 1];

        if let Some(ep) = self.entry_point {
            let mut closest = self.search_layer(&vector, ep, 1, 0);
            for lc in (0..=level.min(self.max_level)).rev() {
                closest = self.search_layer(&vector, closest[0].id, self.config.ef_construction, lc);
                self.insert_into_layer(id, &vector, &closest, lc, &mut connections);
            }
        }

        let node = HnswNode {
            id,
            vector,
            connections,
            level,
        };

        self.nodes.push(node);
        if level > self.max_level {
            self.max_level = level;
            self.entry_point = Some(id);
        }
    }

    /// Search for k nearest neighbors.
    pub fn search(&self, query: &[f32], k: usize) -> Vec<(usize, f32)> {
        if self.entry_point.is_none() || self.nodes.is_empty() {
            return Vec::new();
        }

        let mut ep = self.entry_point.unwrap();
        for level in (self.config.ml as usize..=self.max_level).rev() {
            let changed = self.search_layer(query, ep, 1, level);
            if !changed.is_empty() {
                ep = changed[0].id;
            }
        }

        let results = self.search_layer(query, ep, self.config.ef_search, 0);
        results
            .into_iter()
            .take(k)
            .map(|r| (r.id, r.dist))
            .collect()
    }

    fn random_level(&self) -> usize {
        let mut level = 0;
        while rand::random::<f32>() < self.config.ml && level < 32 {
            level += 1;
        }
        level
    }

    fn search_layer(&self, query: &[f32], entry: usize, ef: usize, layer: usize) -> Vec<HeapItem> {
        let mut visited = vec![false; self.nodes.len()];
        let mut candidates = BinaryHeap::new();
        let mut results = BinaryHeap::new();

        let entry_dist = self.metric.distance(query, &self.nodes[entry].vector);
        candidates.push(Reverse(HeapItem::new(entry, entry_dist)));
        results.push(HeapItem::new(entry, entry_dist));
        visited[entry] = true;

        while let Some(Reverse(current)) = candidates.pop() {
            let current_dist = current.dist;
            let furthest = results.peek().map(|r| r.dist).unwrap_or(f32::MAX);

            if current_dist > furthest {
                break;
            }

            let node = &self.nodes[current.id];
            if let Some(connections) = node.connections.get(layer) {
                for &neighbor in connections {
                    if !visited[neighbor] {
                        visited[neighbor] = true;
                        let dist = self.metric.distance(query, &self.nodes[neighbor].vector);
                        let furthest = results.peek().map(|r| r.dist).unwrap_or(f32::MAX);

                        if dist < furthest || results.len() < ef {
                            candidates.push(Reverse(HeapItem::new(neighbor, dist)));
                            if results.len() < ef {
                                results.push(HeapItem::new(neighbor, dist));
                            } else if dist < furthest {
                                results.pop();
                                results.push(HeapItem::new(neighbor, dist));
                            }
                        }
                    }
                }
            }
        }

        results.into_sorted_vec()
    }

    fn insert_into_layer(
        &mut self,
        id: usize,
        _vector: &[f32],
        closest: &[HeapItem],
        layer: usize,
        connections: &mut [Vec<usize>],
    ) {
        if connections.len() <= layer {
            return;
        }

        let mut neighbors = Vec::new();
        for c in closest {
            neighbors.push((c.id, c.dist));
        }

        neighbors.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(Ordering::Equal));
        neighbors.truncate(self.config.m);

        for &(neighbor_id, _) in &neighbors {
            connections[layer].push(neighbor_id);
            if let Some(node) = self.nodes.get_mut(neighbor_id) {
                if let Some(layer_conns) = node.connections.get_mut(layer) {
                    if !layer_conns.contains(&id) {
                        layer_conns.push(id);
                    }
                }
            }
        }
    }

    /// Get the number of elements in the index.
    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    /// Check if the index is empty.
    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }
}

#[derive(Debug, Clone, Copy)]
struct HeapItem {
    id: usize,
    dist: f32,
}

impl HeapItem {
    fn new(id: usize, dist: f32) -> Self {
        Self { id, dist }
    }
}

impl PartialEq for HeapItem {
    fn eq(&self, other: &Self) -> bool {
        self.dist == other.dist
    }
}

impl Eq for HeapItem {}

impl PartialOrd for HeapItem {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for HeapItem {
    fn cmp(&self, other: &Self) -> Ordering {
        self.dist.partial_cmp(&other.dist).unwrap_or(Ordering::Equal)
    }
}

#[cfg(feature = "qdrant")]
/// Simple HTTP client for Qdrant vector database.
#[derive(Debug, Clone, Default)]
pub struct QdrantClient {
    base_url: String,
    api_key: Option<String>,
    collection: String,
}

#[cfg(feature = "qdrant")]
impl QdrantClient {
    pub fn new(base_url: impl Into<String>, collection: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into().trim_end_matches('/').to_string(),
            api_key: None,
            collection: collection.into(),
        }
    }

    pub fn with_api_key(mut self, api_key: impl Into<String>) -> Self {
        self.api_key = Some(api_key.into());
        self
    }

    /// Upsert vectors into the collection.
    pub async fn upsert(&self, vectors: Vec<(usize, Vec<f32>)>) -> anyhow::Result<()> {
        let url = format!("{}/collections/{}/points", self.base_url, self.collection);
        let payload: Vec<serde_json::Value> = vectors
            .into_iter()
            .map(|(id, vec)| {
                serde_json::json!({
                    "id": id,
                    "vector": vec,
                    "payload": {}
                })
            })
            .collect();

        let body = serde_json::json!({
            "points": payload
        });

        let client = reqwest::Client::new();
        let mut req = client.put(&url).json(&body);
        if let Some(ref key) = self.api_key {
            req = req.header("api-key", key);
        }

        let resp = req.send().await?;
        if !resp.status().is_success() {
            let text = resp.text().await?;
            anyhow::bail!("Qdrant upsert failed: {}", text);
        }
        Ok(())
    }

    /// Search for nearest neighbors.
    pub async fn search(
        &self,
        query: &[f32],
        limit: usize,
    ) -> anyhow::Result<Vec<(usize, f32)>> {
        let url = format!(
            "{}/collections/{}/points/search",
            self.base_url, self.collection
        );

        let body = serde_json::json!({
            "vector": query,
            "limit": limit,
            "with_payload": false
        });

        let client = reqwest::Client::new();
        let mut req = client.post(&url).json(&body);
        if let Some(ref key) = self.api_key {
            req = req.header("api-key", key);
        }

        let resp = req.send().await?;
        if !resp.status().is_success() {
            let text = resp.text().await?;
            anyhow::bail!("Qdrant search failed: {}", text);
        }

        let json: serde_json::Value = resp.json().await?;
        let mut results = Vec::new();
        if let Some(points) = json.get("result").and_then(|r| r.as_array()) {
            for point in points {
                let id = point.get("id").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
                let score = point.get("score").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;
                results.push((id, score));
            }
        }
        Ok(results)
    }

    /// Create a collection if it doesn't exist.
    pub async fn create_collection(&self, dim: usize, distance: DistanceMetric) -> anyhow::Result<()> {
        let url = format!("{}/collections/{}", self.base_url, self.collection);

        let distance_str = match distance {
            DistanceMetric::Cosine => "Cosine",
            DistanceMetric::Euclidean => "Euclidean",
            DistanceMetric::DotProduct => "Dot",
        };

        let body = serde_json::json!({
            "vectors": {
                "size": dim,
                "distance": distance_str
            }
        });

        let client = reqwest::Client::new();
        let mut req = client.put(&url).json(&body);
        if let Some(ref key) = self.api_key {
            req = req.header("api-key", key);
        }

        let resp = req.send().await?;
        if !resp.status().is_success() {
            let text = resp.text().await?;
            anyhow::bail!("Qdrant create collection failed: {}", text);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hnsw_insert_and_search() {
        let config = HnswConfig {
            dim: 4,
            max_elements: 100,
            m: 4,
            ef_construction: 50,
            ef_search: 100,
            ml: 1.0 / 4.0_f32.ln(),
        };
        let mut index = HnswIndex::new(config, DistanceMetric::Euclidean);

        index.insert(0, vec![1.0, 0.0, 0.0, 0.0]);
        index.insert(1, vec![0.0, 1.0, 0.0, 0.0]);
        index.insert(2, vec![0.0, 0.0, 1.0, 0.0]);
        index.insert(3, vec![1.0, 1.0, 1.0, 1.0]);

        let results = index.search(&[1.0, 0.0, 0.0, 0.0], 2);
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].0, 0);
    }

    #[test]
    fn test_distance_metrics() {
        let a = vec![1.0, 0.0];
        let b = vec![0.0, 1.0];

        let euclidean = DistanceMetric::Euclidean.distance(&a, &b);
        assert!((euclidean - 2.0_f32.sqrt()).abs() < 1e-5);

        let cosine = DistanceMetric::Cosine.distance(&a, &b);
        assert!((cosine - 1.0).abs() < 1e-5);
    }
}
