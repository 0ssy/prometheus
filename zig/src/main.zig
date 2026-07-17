const std = @import("std");
const sys = @import("sys.zig");
const ffi = @import("ffi.zig");
const hal = @import("hal.zig");

pub fn build(b: *std.Build) void {
    _ = b;
}

test "sys platform detection" {
    const os = sys.detectOS();
    try std.testing.expect(os != .unknown);
}

test "ffi c string conversion roundtrip" {
    var buf: [256]u8 = undefined;
    var fba = std.heap.FixedBufferAllocator.init(&buf);
    const allocator = fba.allocator();

    const input = "prometheus-hal";
    const c_str = try ffi.toCString(allocator, input);
    defer ffi.freeCString(c_str);
    const back = ffi.fromCString(c_str);
    try std.testing.expectEqualStrings(input, back);
}

test "hal byte order swap" {
    const val: u32 = 0x12345678;
    const swapped = hal.swapEndianU32(val);
    try std.testing.expectEqual(0x78563412, swapped);
}

test "hal bit manipulation" {
    try std.testing.expect(hal.isBitSet(0b1010, 1));
    try std.testing.expect(!hal.isBitSet(0b1010, 0));
    try std.testing.expectEqual(0b1010, hal.setBit(0b1000, 1));
    try std.testing.expectEqual(0b1000, hal.clearBit(0b1010, 1));
}
