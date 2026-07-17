//! P5 Titan AI Platform — CUDA kernel dispatch (Rust/pyo3).
//!
//! Exposes `titan_engine` Python module that dispatches tensor operations
//! through `tensor-engine`, which selects the appropriate backend at runtime.

mod cuda;

#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::PyErr;

#[cfg(feature = "python")]
#[pyfunction]
fn cuda_matmul(a_data: Vec<f32>, a_shape: Vec<usize>, b_data: Vec<f32>, b_shape: Vec<usize>) -> PyResult<Vec<f32>> {
    let a = tensor_engine::Tensor::new(a_shape.clone(), a_data);
    let b = tensor_engine::Tensor::new(b_shape.clone(), b_data);
    let &[m, k1] = a.shape.as_slice() else { return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("matmul needs 2D lhs")); };
    let &[k2, n] = b.shape.as_slice() else { return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("matmul needs 2D rhs")); };
    if k1 != k2 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("matmul inner dims must match"));
    }
    Ok(cuda::matmul(&a.data, &b.data, m as i32, k1 as i32, n as i32))
}

#[cfg(feature = "python")]
#[pyfunction]
fn cuda_add(a_data: Vec<f32>, a_shape: Vec<usize>, b_data: Vec<f32>, b_shape: Vec<usize>) -> PyResult<Vec<f32>> {
    let a = tensor_engine::Tensor::new(a_shape, a_data);
    let b = tensor_engine::Tensor::new(b_shape, b_data);
    if a.shape != b.shape {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("add requires equal shapes"));
    }
    Ok(cuda::add(&a.data, &b.data))
}

#[cfg(feature = "python")]
#[pyfunction]
fn cuda_softmax(data: Vec<f32>, shape: Vec<usize>) -> PyResult<Vec<f32>> {
    let t = tensor_engine::Tensor::new(shape.clone(), data);
    let last_dim = *shape.last().unwrap_or(&0);
    let rows = t.data.len() / last_dim.max(1);
    let mut out = t.data.clone();
    if last_dim > 0 && rows > 0 {
        cuda::softmax(&mut out, rows as i32, last_dim as i32);
    }
    Ok(out)
}

#[cfg(feature = "python")]
#[pyfunction]
fn backend_info() -> PyResult<String> {
    #[cfg(feature = "cuda")]
    {
        Ok("cuda".to_string())
    }
    #[cfg(not(feature = "cuda"))]
    {
        Ok("cpu".to_string())
    }
}

#[cfg(feature = "python")]
#[pymodule]
fn titan_engine(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cuda_matmul, m)?)?;
    m.add_function(wrap_pyfunction!(cuda_add, m)?)?;
    m.add_function(wrap_pyfunction!(cuda_softmax, m)?)?;
    m.add_function(wrap_pyfunction!(backend_info, m)?)?;
    Ok(())
}
