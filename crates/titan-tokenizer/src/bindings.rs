//! Optional Python bindings via `pyo3`.
//!
//! Exposed as the `titan_tokenizer` package when built with `--features python`.

#![cfg(feature = "python")]

use pyo3::prelude::*;
use titan_tokenizer::{decode, encode, list_special_tokens, add_special_tokens, Decoder, Encoder};

/// Encode text to token ids.
#[pyfunction]
fn py_encode(text: &str) -> Vec<u32> {
    encode(text)
}

/// Decode token ids to text.
#[pyfunction]
fn py_decode(ids: Vec<u32>) -> PyResult<String> {
    decode(&ids).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// List default special tokens.
#[pyfunction]
fn py_list_special_tokens() -> PyResult<Vec<(String, u32)>> {
    let set = list_special_tokens();
    Ok(set.tokens)
}

/// Add special tokens and return their ids.
#[pyfunction]
fn py_add_special_tokens(tokens: Vec<&str>) -> Vec<u32> {
    let mut set = list_special_tokens();
    add_special_tokens(&mut set, &tokens.iter().map(|s| *s).collect::<Vec<_>>())
}

#[pymodule]
fn titan_tokenizer(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_encode, m)?)?;
    m.add_function(wrap_pyfunction!(py_decode, m)?)?;
    m.add_function(wrap_pyfunction!(py_list_special_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(py_add_special_tokens, m)?)?;
    Ok(())
}
