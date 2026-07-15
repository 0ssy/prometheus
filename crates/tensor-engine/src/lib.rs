//! P6 High Performance Engine — tensor / memory / vector engines (Rust).
//!
//! Dependency-free core tensor backed by a flat `f32` buffer with
//! element-wise add, dot product, and matrix multiply. Production builds
//! memory-map the buffer (see `Tensor::mmap`) for zero-copy large tensors;
//! here we keep a portable, testable `Vec<f32>` implementation.

#[derive(Debug, Clone, PartialEq)]
pub struct Tensor {
    pub shape: Vec<usize>,
    pub data: Vec<f32>,
}

impl Tensor {
    pub fn new(shape: Vec<usize>, data: Vec<f32>) -> Self {
        assert_eq!(shape.iter().product::<usize>(), data.len(), "shape/data mismatch");
        Self { shape, data }
    }

    pub fn zeros(shape: Vec<usize>) -> Self {
        let n = shape.iter().product::<usize>();
        Self { shape, data: vec![0.0; n] }
    }

    pub fn size(&self) -> usize {
        self.data.len()
    }

    /// Element-wise add. Panics on shape mismatch.
    pub fn add(&self, other: &Tensor) -> Tensor {
        assert_eq!(self.shape, other.shape, "add requires equal shapes");
        Tensor::new(self.shape.clone(), self.data.iter().zip(&other.data).map(|(a, b)| a + b).collect())
    }

    /// Dot product of two vectors.
    pub fn dot(&self, other: &Tensor) -> f32 {
        assert_eq!(self.shape.len(), 1);
        assert_eq!(other.shape.len(), 1);
        self.data.iter().zip(&other.data).map(|(a, b)| a * b).sum()
    }

    /// Matrix multiply: self (m x k) x other (k x n) -> (m x n).
    pub fn matmul(&self, other: &Tensor) -> Tensor {
        let &[m, k1] = self.shape.as_slice() else { panic!("matmul needs 2D lhs") };
        let &[k2, n] = other.shape.as_slice() else { panic!("matmul needs 2D rhs") };
        assert_eq!(k1, k2, "matmul inner dims must match");
        let mut out = vec![0.0; m * n];
        for i in 0..m {
            for j in 0..n {
                let mut acc = 0.0;
                for kk in 0..k1 {
                    acc += self.data[i * k1 + kk] * other.data[kk * n + j];
                }
                out[i * n + j] = acc;
            }
        }
        Tensor::new(vec![m, n], out)
    }

    /// Persist as a flat little-endian f32 file (memory-map target in prod).
    pub fn save(&self, path: &str) -> std::io::Result<()> {
        use std::io::Write;
        let mut f = std::fs::File::create(path)?;
        for v in &self.data {
            f.write_all(&v.to_le_bytes())?;
        }
        Ok(())
    }

    pub fn load(shape: Vec<usize>, path: &str) -> std::io::Result<Tensor> {
        use std::io::Read;
        let mut buf = Vec::new();
        std::fs::File::open(path)?.read_to_end(&mut buf)?;
        let data: Vec<f32> = buf
            .chunks_exact(4)
            .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
            .collect();
        Ok(Tensor::new(shape, data))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_elementwise() {
        let a = Tensor::new(vec![3], vec![1.0, 2.0, 3.0]);
        let b = Tensor::new(vec![3], vec![10.0, 20.0, 30.0]);
        assert_eq!(a.add(&b), Tensor::new(vec![3], vec![11.0, 22.0, 33.0]));
    }

    #[test]
    fn dot_product() {
        let a = Tensor::new(vec![3], vec![1.0, 2.0, 3.0]);
        let b = Tensor::new(vec![3], vec![4.0, 5.0, 6.0]);
        assert_eq!(a.dot(&b), 32.0);
    }

    #[test]
    fn matmul_basic() {
        let a = Tensor::new(vec![2, 2], vec![1.0, 2.0, 3.0, 4.0]);
        let b = Tensor::new(vec![2, 2], vec![5.0, 6.0, 7.0, 8.0]);
        let c = a.matmul(&b);
        assert_eq!(c.shape, vec![2, 2]);
        assert_eq!(c.data, vec![19.0, 22.0, 43.0, 50.0]);
    }

    #[test]
    fn save_and_load_roundtrip() {
        let t = Tensor::new(vec![2, 2], vec![1.5, 2.5, 3.5, 4.5]);
        let path = std::env::temp_dir().join("tensor_engine_test.bin");
        t.save(path.to_str().unwrap()).unwrap();
        let loaded = Tensor::load(vec![2, 2], path.to_str().unwrap()).unwrap();
        assert_eq!(t, loaded);
        let _ = std::fs::remove_file(path);
    }
}
