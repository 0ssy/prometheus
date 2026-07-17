//! P5 Titan AI Platform — CUDA kernel dispatch (Rust/pyo3).
//!
//! Exposes `titan_engine` Python module that dispatches tensor operations
//! through `tensor-engine`, which selects the appropriate backend at runtime.

use pyo3::prelude::*;
use pyo3::PyErr;

#[pyfunction]
fn cuda_matmul(a_data: Vec<f32>, a_shape: Vec<usize>, b_data: Vec<f32>, b_shape: Vec<usize>) -> PyResult<Vec<f32>> {
    let a = tensor_engine::Tensor::new(a_shape.clone(), a_data);
    let b = tensor_engine::Tensor::new(b_shape.clone(), b_data);
    let &[m, k1] = a.shape.as_slice() else { return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("matmul needs 2D lhs")); };
    let &[k2, n] = b.shape.as_slice() else { return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("matmul needs 2D rhs")); };
    if k1 != k2 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("matmul inner dims must match"));
    }
    Ok(a.matmul(&b).data)
}

#[pyfunction]
fn cuda_add(a_data: Vec<f32>, a_shape: Vec<usize>, b_data: Vec<f32>, b_shape: Vec<usize>) -> PyResult<Vec<f32>> {
    let a = tensor_engine::Tensor::new(a_shape, a_data);
    let b = tensor_engine::Tensor::new(b_shape, b_data);
    if a.shape != b.shape {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("add requires equal shapes"));
    }
    Ok(a.add(&b).data)
}

#[pyfunction]
fn cuda_softmax(data: Vec<f32>, shape: Vec<usize>) -> PyResult<Vec<f32>> {
    let t = tensor_engine::Tensor::new(shape, data);
    Ok(t.softmax().data)
}

#[pyfunction]
fn backend_info() -> PyResult<String> {
    Ok("cpu".to_string())
}

#[pymodule]
fn titan_engine(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cuda_matmul, m)?)?;
    m.add_function(wrap_pyfunction!(cuda_add, m)?)?;
    m.add_function(wrap_pyfunction!(cuda_softmax, m)?)?;
    m.add_function(wrap_pyfunction!(backend_info, m)?)?;
    Ok(())
}
