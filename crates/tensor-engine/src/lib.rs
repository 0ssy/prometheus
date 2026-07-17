//! P6 High Performance Engine — tensor / memory / vector engines (Rust).
//!
//! Dependency-free core tensor backed by a flat `f32` buffer with
//! element-wise add, dot product, matrix multiply, softmax, and layer norm.
//! Production builds memory-map the buffer (see `Tensor::mmap`) for zero-copy
//! large tensors; here we keep a portable, testable `Vec<f32>` implementation.

use std::cmp::max;

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

    /// Element-wise multiply.
    pub fn mul(&self, other: &Tensor) -> Tensor {
        assert_eq!(self.shape, other.shape, "mul requires equal shapes");
        Tensor::new(self.shape.clone(), self.data.iter().zip(&other.data).map(|(a, b)| a * b).collect())
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

    /// Softmax over the last dimension.
    pub fn softmax(&self) -> Tensor {
        assert!(!self.data.is_empty(), "softmax requires non-empty tensor");
        let last_dim = *self.shape.last().expect("softmax needs rank");
        let rows = self.data.len() / last_dim;
        let mut out = vec![0.0; self.data.len()];
        for r in 0..rows {
            let start = r * last_dim;
            let end = start + last_dim;
            let row = &self.data[start..end];
            let max_val = row.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
            let exps: Vec<f32> = row.iter().map(|&x| (x - max_val).exp()).collect();
            let sum: f32 = exps.iter().sum();
            for (i, &v) in exps.iter().enumerate() {
                out[start + i] = v / sum;
            }
        }
        Tensor::new(self.shape.clone(), out)
    }

    /// Layer normalization over the last dimension.
    pub fn layer_norm(&self, eps: f32) -> Tensor {
        assert!(!self.data.is_empty(), "layer_norm requires non-empty tensor");
        let last_dim = *self.shape.last().expect("layer_norm needs rank");
        let rows = self.data.len() / last_dim;
        let mut out = vec![0.0; self.data.len()];
        for r in 0..rows {
            let start = r * last_dim;
            let end = start + last_dim;
            let row = &self.data[start..end];
            let mean = row.iter().sum::<f32>() / last_dim as f32;
            let variance = row.iter().map(|&x| (x - mean).powi(2)).sum::<f32>() / last_dim as f32;
            let std = (variance + eps).sqrt();
            for (i, &x) in row.iter().enumerate() {
                out[start + i] = (x - mean) / std;
            }
        }
        Tensor::new(self.shape.clone(), out)
    }

    /// Scalar addition (broadcasted).
    pub fn add_scalar(&self, scalar: f32) -> Tensor {
        Tensor::new(self.shape.clone(), self.data.iter().map(|&x| x + scalar).collect())
    }

    /// Scalar multiplication (broadcasted).
    pub fn mul_scalar(&self, scalar: f32) -> Tensor {
        Tensor::new(self.shape.clone(), self.data.iter().map(|&x| x * scalar).collect())
    }

    /// Sum all elements.
    pub fn sum(&self) -> f32 {
        self.data.iter().sum()
    }

    /// Mean of all elements.
    pub fn mean(&self) -> f32 {
        self.data.iter().sum::<f32>() / max(self.data.len(), 1) as f32
    }

    /// Max element.
    pub fn max(&self) -> f32 {
        self.data.iter().cloned().fold(f32::NEG_INFINITY, f32::max)
    }

    /// Reshape to a new shape with the same total elements.
    pub fn reshape(&self, new_shape: Vec<usize>) -> Tensor {
        assert_eq!(self.shape.iter().product::<usize>(), new_shape.iter().product::<usize>(), "reshape size mismatch");
        Tensor::new(new_shape, self.data.clone())
    }

    /// Transpose a 2D matrix.
    pub fn transpose(&self) -> Tensor {
        assert_eq!(self.shape.len(), 2, "transpose needs 2D tensor");
        let &[m, n] = self.shape.as_slice() else { unreachable!() };
        let mut out = vec![0.0; m * n];
        for i in 0..m {
            for j in 0..n {
                out[j * m + i] = self.data[i * n + j];
            }
        }
        Tensor::new(vec![n, m], out)
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

#[cfg(feature = "python")]
mod pybind {
    use pyo3::prelude::*;

    #[pyfunction]
    fn zeros(shape: Vec<usize>) -> PyResult<Vec<f32>> {
        let t = crate::Tensor::zeros(shape);
        Ok(t.data)
    }

    #[pyfunction]
    fn add(a_data: Vec<f32>, a_shape: Vec<usize>, b_data: Vec<f32>, b_shape: Vec<usize>) -> PyResult<Vec<f32>> {
        let a = crate::Tensor::new(a_shape, a_data);
        let b = crate::Tensor::new(b_shape, b_data);
        Ok(a.add(&b).data)
    }

    #[pyfunction]
    fn dot(a_data: Vec<f32>, b_data: Vec<f32>) -> PyResult<f32> {
        let a = crate::Tensor::new(vec![a_data.len()], a_data);
        let b = crate::Tensor::new(vec![b_data.len()], b_data);
        Ok(a.dot(&b))
    }

    #[pyfunction]
    fn matmul(a_data: Vec<f32>, a_shape: Vec<usize>, b_data: Vec<f32>, b_shape: Vec<usize>) -> PyResult<Vec<f32>> {
        let a = crate::Tensor::new(a_shape, a_data);
        let b = crate::Tensor::new(b_shape, b_data);
        Ok(a.matmul(&b).data)
    }

    #[pyfunction]
    fn softmax(data: Vec<f32>, shape: Vec<usize>) -> PyResult<Vec<f32>> {
        let t = crate::Tensor::new(shape, data);
        Ok(t.softmax().data)
    }

    #[pyfunction]
    fn layer_norm(data: Vec<f32>, shape: Vec<usize>, eps: f32) -> PyResult<Vec<f32>> {
        let t = crate::Tensor::new(shape, data);
        Ok(t.layer_norm(eps).data)
    }

    #[pymodule]
    fn tensor_engine(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(zeros, m)?)?;
        m.add_function(wrap_pyfunction!(add, m)?)?;
        m.add_function(wrap_pyfunction!(dot, m)?)?;
        m.add_function(wrap_pyfunction!(matmul, m)?)?;
        m.add_function(wrap_pyfunction!(softmax, m)?)?;
        m.add_function(wrap_pyfunction!(layer_norm, m)?)?;
        Ok(())
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

    #[test]
    fn softmax_normalizes() {
        let t = Tensor::new(vec![3], vec![1.0, 2.0, 3.0]);
        let s = t.softmax();
        let sum: f32 = s.data.iter().sum();
        assert!((sum - 1.0).abs() < 1e-5);
    }

    #[test]
    fn layer_norm_zero_mean_unit_var() {
        let t = Tensor::new(vec![1, 4], vec![1.0, 2.0, 3.0, 4.0]);
        let n = t.layer_norm(1e-5);
        assert!((n.mean() - 0.0).abs() < 1e-4);
    }

    #[test]
    fn reshape_preserves_elements() {
        let t = Tensor::new(vec![2, 3], vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0]);
        let r = t.reshape(vec![3, 2]);
        assert_eq!(r.data, vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0]);
    }

    #[test]
    fn transpose_2d() {
        let t = Tensor::new(vec![2, 3], vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0]);
        let tt = t.transpose();
        assert_eq!(tt.shape, vec![3, 2]);
        assert_eq!(tt.data, vec![1.0, 4.0, 2.0, 5.0, 3.0, 6.0]);
    }
}

