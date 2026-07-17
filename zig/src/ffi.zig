const std = @import("std");

pub fn toCString(allocator: std.mem.Allocator, zig_str: []const u8) ![*:0]const u8 {
    const buf = try allocator.alloc(u8, zig_str.len + 1);
    errdefer allocator.free(buf);
    for (zig_str, 0..) |c, i| {
        buf[i] = c;
    }
    buf[zig_str.len] = 0;
    return @ptrCast(buf.ptr);
}

pub fn fromCString(c_ptr: [*:0]const u8) []const u8 {
    return std.mem.span(c_ptr);
}

pub fn freeCString(c_ptr: [*:0]const u8) void {
    _ = c_ptr;
}

pub fn boolToInt(b: bool) c_int {
    return if (b) 1 else 0;
}

pub fn intToBool(i: c_int) bool {
    return i != 0;
}

pub fn sliceToPtr(slice: []const u8) [*]const u8 {
    return slice.ptr;
}

pub fn ptrLenToSlice(ptr: [*]const u8, len: usize) []const u8 {
    return ptr[0..len];
}

pub const Callback = *const fn (?*anyopaque, [*]const u8, usize) void;

pub fn invokeCallback(ctx: ?*anyopaque, cb: Callback, data: []const u8) void {
    cb(ctx, data.ptr, data.len);
}

pub fn externFn(name: []const u8, signature: []const u8) void {
    _ = name;
    _ = signature;
}
