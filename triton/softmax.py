import triton
import triton.language as tl
import torch

@triton.jit
def softmax_kernel(
    x_ptr, out_ptr, rows, cols,
    stride_x, stride_out
):
    row = tl.program_id(0)
    cols_range = tl.arange(0, cols)
    x = tl.load(x_ptr + row * stride_x + cols_range)
    mx = tl.max(x, axis=0)
    e = tl.exp(x - mx)
    s = tl.sum(e, axis=0)
    y = e / s
    tl.store(out_ptr + row * stride_out + cols_range, y)

def triton_softmax(x: torch.Tensor) -> torch.Tensor:
    rows, cols = x.shape
    out = torch.empty_like(x)
    grid = (rows,)
    softmax_kernel[grid](x, out, rows, cols, x.stride(0), out.stride(0))
    return out
