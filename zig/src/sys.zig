const std = @import("std");

pub const OS = enum {
    windows,
    linux,
    macos,
    unknown,
};

const builtin = @import("builtin");

pub fn detectOS() OS {
    return switch (builtin.os.tag) {
        .windows => .windows,
        .linux => .linux,
        .macos => .macos,
        else => .unknown,
    };
}

pub fn detectArch() []const u8 {
    return switch (builtin.cpu.arch) {
        .x86_64 => "x86_64",
        .aarch64 => "aarch64",
        .arm => "arm",
        .i386 => "x86",
        else => "unknown",
    };
}

pub fn pathSeparator() u8 {
    return switch (detectOS()) {
        .windows => '\\',
        else => '/',
    };
}

pub fn joinPath(allocator: std.mem.Allocator, parts: []const []const u8) ![]u8 {
    const sep = pathSeparator();
    var buf = std.ArrayList(u8).init(allocator);
    defer buf.deinit();

    for (parts, 0..) |part, i| {
        try buf.writer().writeAll(part);
        if (i < parts.len - 1) {
            try buf.append(sep);
        }
    }
    return buf.toOwnedSlice();
}

pub const ProcessResult = struct {
    stdout: []u8,
    stderr: []u8,
    exit_code: u32,
    timed_out: bool,
};

pub fn runCommand(allocator: std.mem.Allocator, argv: []const []const u8, timeout_ms: ?u64) !ProcessResult {
    var child = std.process.Child.init(argv, allocator);
    child.stdin_behavior = .Ignore;
    child.stdout_behavior = .Pipe;
    child.stderr_behavior = .Pipe;

    const term = child.spawn() catch |err| {
        return ProcessResult{
            .stdout = "",
            .stderr = try std.fmt.allocPrint(allocator, "spawn failed: {s}", .{@errorName(err)}),
            .exit_code = 127,
            .timed_out = false,
        };
    };

    var stdout_buf = std.ArrayList(u8).init(allocator);
    var stderr_buf = std.ArrayList(u8).init(allocator);
    defer stdout_buf.deinit();
    defer stderr_buf.deinit();

    if (timeout_ms) |ms| {
        const result = child.waitTimeout(ms * std.time.ns_per_ms) catch |err| switch (err) {
            error.Timeout => {
                _ = child.kill() catch {};
                _ = child.wait() catch {};
                return ProcessResult{
                    .stdout = stdout_buf.toOwnedSlice() catch "",
                    .stderr = try std.fmt.allocPrint(allocator, "process timed out after {d}ms", .{ms}),
                    .exit_code = 124,
                    .timed_out = true,
                };
            },
        } catch unreachable;
        _ = result;
    } else {
        const r = child.wait() catch |err| {
            return ProcessResult{
                .stdout = stdout_buf.toOwnedSlice() catch "",
                .stderr = try std.fmt.allocPrint(allocator, "wait failed: {s}", .{@errorName(err)}),
                .exit_code = 127,
                .timed_out = false,
            };
        };
        _ = r;
    }

    _ = term;

    return ProcessResult{
        .stdout = stdout_buf.toOwnedSlice() catch "",
        .stderr = stderr_buf.toOwnedSlice() catch "",
        .exit_code = 0,
        .timed_out = false,
    };
}
