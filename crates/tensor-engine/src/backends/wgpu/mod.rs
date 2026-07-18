//! WGPU-based GPU compute backend for tensor operations.
//!
//! Feature-gated behind `wgpu`. Provides cross-platform GPU compute
//! via Vulkan, Metal, DX12, or WebGPU.

#[cfg(feature = "wgpu")]
use std::sync::Arc;

#[cfg(feature = "wgpu")]
pub mod wgpu_backend {
    use super::*;

    /// WGPU compute context. Lazily initialized.
    pub struct WgpuContext {
        pub device: Arc<wgpu::Device>,
        pub queue: Arc<wgpu::Queue>,
        pub _adapter: Arc<wgpu::Adapter>,
    }

    impl WgpuContext {
        /// Initialize WGPU adapter, device, and queue.
        pub async fn new() -> anyhow::Result<Self> {
            let instance = wgpu::Instance::default();
            let adapter = instance
                .request_adapter(&wgpu::RequestAdapterOptions {
                    power_preference: wgpu::PowerPreference::HighPerformance,
                    compatible_surface: None,
                    force_fallback_adapter: false,
                })
                .await
                .ok_or_else(|| anyhow::anyhow!("no GPU adapter found"))?;

            let adapter = Arc::new(adapter);
            let (device, queue) = adapter
                .request_device(
                    &wgpu::DeviceDescriptor {
                        label: Some("tensor-engine-wgpu"),
                        required_features: wgpu::Features::empty(),
                        required_limits: wgpu::Limits::downlevel_defaults(),
                        memory_hints: Default::default(),
                    },
                    None,
                )
                .await?;

            Ok(Self {
                device: Arc::new(device),
                queue: Arc::new(queue),
                _adapter: adapter,
            })
        }
    }

    /// Element-wise add on GPU.
    pub async fn add(ctx: &WgpuContext, a: &[f32], b: &[f32]) -> anyhow::Result<Vec<f32>> {
        let n = a.len();
        assert_eq!(n, b.len());

        let shader = ctx.device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("add shader"),
            source: wgpu::ShaderSource::Wgsl(std::borrow::Cow::Borrowed(include_str!(
                "shaders/add.wgsl"
            ))),
        });

        let bind_group_layout = ctx.device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("add layout"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 2,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: false },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
            ],
        });

        let pipeline_layout = ctx
            .device
            .create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("add layout"),
                bind_group_layouts: &[&bind_group_layout],
                push_constant_ranges: &[],
            });

        let pipeline = ctx
            .device
            .create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
                label: Some("add pipeline"),
                layout: Some(&pipeline_layout),
                module: &shader,
                entry_point: "main",
                compilation_options: Default::default(),
                cache: None,
            });

        let a_buf = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("a buffer"),
            size: (n * 4) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: true,
        });
        {
            let mut map = a_buf.slice(..).get_mapped_range_mut();
            map.copy_from_slice(bytemuck::cast_slice(a));
        }

        let b_buf = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("b buffer"),
            size: (n * 4) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: true,
        });
        {
            let mut map = b_buf.slice(..).get_mapped_range_mut();
            map.copy_from_slice(bytemuck::cast_slice(b));
        }

        let out_buf = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("out buffer"),
            size: (n * 4) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });

        let bind_group = ctx.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("add bind group"),
            layout: &bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: a_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: b_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 2,
                    resource: out_buf.as_entire_binding(),
                },
            ],
        });

        let mut encoder = ctx
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("add encoder"),
            });
        {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("add pass"),
                timestamp_writes: None,
            });
            pass.set_pipeline(&pipeline);
            pass.set_bind_group(0, &bind_group, &[]);
            pass.dispatch_workgroups((n as u32 + 63) / 64, 1, 1);
        }

        let staging = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("staging"),
            size: (n * 4) as u64,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        encoder.copy_buffer_to_buffer(&out_buf, 0, &staging, 0, (n * 4) as u64);
        ctx.queue.submit(Some(encoder.finish()));

        let slice = staging.slice(..);
        slice.map_async(wgpu::MapMode::Read, |_| {});
        ctx.device.poll(wgpu::Maintain::Poll);
        let data = slice.get_mapped_range().to_vec();
        Ok(bytemuck::cast_slice(&data).to_vec())
    }

    /// Element-wise mul on GPU.
    pub async fn mul(ctx: &WgpuContext, a: &[f32], b: &[f32]) -> anyhow::Result<Vec<f32>> {
        let n = a.len();
        assert_eq!(n, b.len());

        let shader = ctx.device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("mul shader"),
            source: wgpu::ShaderSource::Wgsl(std::borrow::Cow::Borrowed(include_str!(
                "shaders/mul.wgsl"
            ))),
        });

        let bind_group_layout = ctx.device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("mul layout"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 2,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: false },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
            ],
        });

        let pipeline_layout = ctx
            .device
            .create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("mul layout"),
                bind_group_layouts: &[&bind_group_layout],
                push_constant_ranges: &[],
            });

        let pipeline = ctx
            .device
            .create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
                label: Some("mul pipeline"),
                layout: Some(&pipeline_layout),
                module: &shader,
                entry_point: "main",
                compilation_options: Default::default(),
                cache: None,
            });

        let a_buf = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("a buffer"),
            size: (n * 4) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: true,
        });
        {
            let mut map = a_buf.slice(..).get_mapped_range_mut();
            map.copy_from_slice(bytemuck::cast_slice(a));
        }

        let b_buf = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("b buffer"),
            size: (n * 4) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: true,
        });
        {
            let mut map = b_buf.slice(..).get_mapped_range_mut();
            map.copy_from_slice(bytemuck::cast_slice(b));
        }

        let out_buf = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("out buffer"),
            size: (n * 4) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });

        let bind_group = ctx.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("mul bind group"),
            layout: &bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: a_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: b_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 2,
                    resource: out_buf.as_entire_binding(),
                },
            ],
        });

        let mut encoder = ctx
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("mul encoder"),
            });
        {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("mul pass"),
                timestamp_writes: None,
            });
            pass.set_pipeline(&pipeline);
            pass.set_bind_group(0, &bind_group, &[]);
            pass.dispatch_workgroups((n as u32 + 63) / 64, 1, 1);
        }

        let staging = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("staging"),
            size: (n * 4) as u64,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        encoder.copy_buffer_to_buffer(&out_buf, 0, &staging, 0, (n * 4) as u64);
        ctx.queue.submit(Some(encoder.finish()));

        let slice = staging.slice(..);
        slice.map_async(wgpu::MapMode::Read, |_| {});
        ctx.device.poll(wgpu::Maintain::Poll);
        let data = slice.get_mapped_range().to_vec();
        Ok(bytemuck::cast_slice(&data).to_vec())
    }

    /// Matrix multiply on GPU: (M x K) * (K x N) -> (M x N).
    pub async fn matmul(ctx: &WgpuContext, a: &[f32], b: &[f32], m: usize, k: usize, n: usize) -> anyhow::Result<Vec<f32>> {
        let shader = ctx.device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("matmul shader"),
            source: wgpu::ShaderSource::Wgsl(std::borrow::Cow::Borrowed(include_str!(
                "shaders/matmul.wgsl"
            ))),
        });

        let bind_group_layout = ctx.device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("matmul layout"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 2,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: false },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 3,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform { dynamic: false, min_binding_size: None },
                        has_dynamic_offset: false,
                        min_binding_size: std::num::NonZeroU64::new(12),
                    },
                    count: None,
                },
            ],
        });

        let pipeline_layout = ctx
            .device
            .create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("matmul layout"),
                bind_group_layouts: &[&bind_group_layout],
                push_constant_ranges: &[],
            });

        let pipeline = ctx
            .device
            .create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
                label: Some("matmul pipeline"),
                layout: Some(&pipeline_layout),
                module: &shader,
                entry_point: "main",
                compilation_options: Default::default(),
                cache: None,
            });

        let a_buf = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("a buffer"),
            size: (m * k * 4) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: true,
        });
        {
            let mut map = a_buf.slice(..).get_mapped_range_mut();
            map.copy_from_slice(bytemuck::cast_slice(a));
        }

        let b_buf = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("b buffer"),
            size: (k * n * 4) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: true,
        });
        {
            let mut map = b_buf.slice(..).get_mapped_range_mut();
            map.copy_from_slice(bytemuck::cast_slice(b));
        }

        let out_buf = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("out buffer"),
            size: (m * n * 4) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });

        let params = [m as u32, k as u32, n as u32];
        let params_buf = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("params buffer"),
            size: 12,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: true,
        });
        {
            let mut map = params_buf.slice(..).get_mapped_range_mut();
            map.copy_from_slice(bytemuck::cast_slice(&params));
        }

        let bind_group = ctx.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("matmul bind group"),
            layout: &bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: a_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: b_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 2,
                    resource: out_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 3,
                    resource: params_buf.as_entire_binding(),
                },
            ],
        });

        let workgroups = ((m * n) as u32 + 63) / 64;
        let mut encoder = ctx
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("matmul encoder"),
            });
        {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("matmul pass"),
                timestamp_writes: None,
            });
            pass.set_pipeline(&pipeline);
            pass.set_bind_group(0, &bind_group, &[]);
            pass.dispatch_workgroups(workgroups, 1, 1);
        }

        let staging = ctx.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("staging"),
            size: (m * n * 4) as u64,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        encoder.copy_buffer_to_buffer(&out_buf, 0, &staging, 0, (m * n * 4) as u64);
        ctx.queue.submit(Some(encoder.finish()));

        let slice = staging.slice(..);
        slice.map_async(wgpu::MapMode::Read, |_| {});
        ctx.device.poll(wgpu::Maintain::Poll);
        let data = slice.get_mapped_range().to_vec();
        Ok(bytemuck::cast_slice(&data).to_vec())
    }
}

#[cfg(not(feature = "wgpu"))]
pub mod wgpu_backend {
    pub async fn add(_ctx: &(), a: &[f32], b: &[f32]) -> Result<Vec<f32>, ()> {
        Ok(a.iter().zip(b.iter()).map(|(&x, &y)| x + y).collect())
    }

    pub async fn mul(_ctx: &(), a: &[f32], b: &[f32]) -> Result<Vec<f32>, ()> {
        Ok(a.iter().zip(b.iter()).map(|(&x, &y)| x * y).collect())
    }

    pub async fn matmul(_ctx: &(), a: &[f32], b: &[f32], _m: usize, _k: usize, _n: usize) -> Result<Vec<f32>, ()> {
        let len = _m * _n;
        let mut out = vec![0.0f32; len];
        for i in 0.._m {
            for j in 0.._n {
                let mut acc = 0.0;
                for kk in 0.._k {
                    acc += a[i * _k + kk] * b[kk * _n + j];
                }
                out[i * _n + j] = acc;
            }
        }
        Ok(out)
    }
}

pub use wgpu_backend::{add as wgpu_add, mul as wgpu_mul, matmul as wgpu_matmul};
