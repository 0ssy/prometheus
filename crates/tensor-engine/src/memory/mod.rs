//! P6 Memory Allocator — arena allocator and memory-mapped tensor buffers.
//!
//! Provides:
//! - `ArenaAllocator`: bump-pointer arena for temporary tensor allocations
//! - `MmapTensor`: memory-mapped model weights via `memmap2`

use std::alloc::{alloc, dealloc, Layout};
use std::mem;
use std::ptr::NonNull;

/// Supported data types for memory-mapped tensors.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum DType {
    F32,
    F16,
    BF16,
    I32,
    U32,
}

impl DType {
    pub fn size_of(&self) -> usize {
        match self {
            DType::F32 => 4,
            DType::F16 => 2,
            DType::BF16 => 2,
            DType::I32 => 4,
            DType::U32 => 4,
        }
    }
}

/// Simple bump-pointer arena allocator for tensor buffers.
///
/// All allocations are freed all at once when the arena is reset.
/// This is ideal for temporary tensors during inference.
pub struct ArenaAllocator {
    buffer: NonNull<u8>,
    capacity: usize,
    offset: usize,
}

impl ArenaAllocator {
    /// Create a new arena with the given capacity in bytes.
    pub fn new(capacity: usize) -> Option<Self> {
        let layout = Layout::from_size_align(capacity, 64).ok()?;
        let ptr = unsafe { alloc(layout) };
        let ptr = NonNull::new(ptr)?;
        Some(Self {
            buffer: ptr,
            capacity,
            offset: 0,
        })
    }

    /// Allocate a tensor buffer of `count * size_of::<T>()` bytes.
    /// Returns a mutable pointer to the allocated region.
    pub fn allocate<T>(&mut self, count: usize) -> Option<NonNull<T>> {
        let size = count * mem::size_of::<T>();
        let align = mem::align_of::<T>();

        // Align the offset
        let aligned_offset = (self.offset + align - 1) & !(align - 1);
        if aligned_offset + size > self.capacity {
            return None;
        }

        let ptr = unsafe { self.buffer.as_ptr().add(aligned_offset) };
        self.offset = aligned_offset + size;
        NonNull::new(ptr as *mut T)
    }

    /// Reset the arena, making all allocations available again.
    pub fn reset(&mut self) {
        self.offset = 0;
    }

    /// Get the current used bytes.
    pub fn used(&self) -> usize {
        self.offset
    }

    /// Get the total capacity in bytes.
    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Get the remaining bytes.
    pub fn remaining(&self) -> usize {
        self.capacity - self.offset
    }
}

impl Drop for ArenaAllocator {
    fn drop(&mut self) {
        if self.capacity > 0 {
            let layout = Layout::from_size_align(self.capacity, 64).unwrap();
            unsafe { dealloc(self.buffer.as_ptr(), layout) };
        }
    }
}

#[cfg(feature = "memmap")]
pub mod mmap_backend {
    use super::*;
    use memmap2::MmapOptions;

    /// Memory-mapped tensor buffer for model weights.
    ///
    /// Allows zero-copy access to large model weight files.
    pub struct MmapTensor {
        pub shape: Vec<usize>,
        pub data: memmap2::Mmap,
        pub dtype: DType,
    }

    impl MmapTensor {
        /// Memory-map a flat tensor file.
        ///
        /// File format: [shape_len: u32][shape: u32[]][data: dtype[]]
        pub fn open(path: &str) -> std::io::Result<Self> {
            let file = std::fs::File::open(path)?;

            let header_len = {
                let mmap = unsafe { MmapOptions::new().map(&file)? };
                let shape_len = u32::from_le_bytes([
                    mmap[0],
                    mmap[1],
                    mmap[2],
                    mmap[3],
                ]) as usize;
                let mut offset = 4;
                for _ in 0..shape_len {
                    offset += 4;
                }
                offset
            };

            let shape = {
                let mmap = unsafe { MmapOptions::new().map(&file)? };
                let shape_len = u32::from_le_bytes([
                    mmap[0],
                    mmap[1],
                    mmap[2],
                    mmap[3],
                ]) as usize;
                let mut shape = Vec::with_capacity(shape_len);
                let mut offset = 4;
                for _ in 0..shape_len {
                    let dim = u32::from_le_bytes([
                        mmap[offset],
                        mmap[offset + 1],
                        mmap[offset + 2],
                        mmap[offset + 3],
                    ]) as usize;
                    shape.push(dim);
                    offset += 4;
                }
                shape
            };

            let data = unsafe { MmapOptions::new().offset(header_len).map(&file)? };
            let dtype = DType::F32;

            Ok(Self { shape, data, dtype })
        }

        /// Get the total number of elements.
        pub fn len(&self) -> usize {
            self.shape.iter().product()
        }

        /// Check if the tensor is empty.
        pub fn is_empty(&self) -> bool {
            self.shape.is_empty() || self.shape.iter().product::<usize>() == 0
        }

        /// Read an f32 value at the given index.
        pub fn read_f32(&self, index: usize) -> f32 {
            let offset = index * 4;
            f32::from_le_bytes([
                self.data[offset],
                self.data[offset + 1],
                self.data[offset + 2],
                self.data[offset + 3],
            ])
        }
    }
}

#[cfg(not(feature = "memmap"))]
pub mod mmap_backend {
    use super::*;

    /// Fallback when memmap feature is not enabled.
    pub struct MmapTensor {
        pub shape: Vec<usize>,
        pub data: Vec<f32>,
        pub dtype: DType,
    }

    impl MmapTensor {
        pub fn open(_path: &str) -> std::io::Result<Self> {
            Err(std::io::Error::new(
                std::io::ErrorKind::Unsupported,
                "memmap feature not enabled",
            ))
        }

        pub fn len(&self) -> usize {
            self.data.len()
        }

        pub fn is_empty(&self) -> bool {
            self.data.is_empty()
        }

        pub fn read_f32(&self, index: usize) -> f32 {
            self.data[index]
        }
    }
}

pub use mmap_backend::MmapTensor;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_arena_allocate_and_reset() {
        let mut arena = ArenaAllocator::new(1024).unwrap();
        assert_eq!(arena.remaining(), 1024);

        let p1 = arena.allocate::<f32>(256);
        assert!(p1.is_some());
        assert_eq!(arena.remaining(), 1024 - 256 * 4);

        arena.reset();
        assert_eq!(arena.remaining(), 1024);

        let p2 = arena.allocate::<f32>(256);
        assert!(p2.is_some());
        assert_eq!(arena.remaining(), 1024 - 256 * 4);
    }

    #[test]
    fn test_arena_exhaustion() {
        let mut arena = ArenaAllocator::new(1024).unwrap();
        let p1 = arena.allocate::<f32>(64);
        assert!(p1.is_some());
        let p2 = arena.allocate::<f32>(64);
        assert!(p2.is_some());
        let p3 = arena.allocate::<f32>(64);
        assert!(p3.is_some());
        let p4 = arena.allocate::<f32>(64);
        assert!(p4.is_some());
        let p5 = arena.allocate::<f32>(1);
        assert!(p5.is_none());
    }
}
