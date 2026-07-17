const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const hal_mod = b.createModule(.{
        .root_source_file = b.path("src/hal.zig"),
        .target = target,
        .optimize = optimize,
    });
    const hal_core = b.addLibrary(.{
        .name = "hal_core_zig",
        .root_module = hal_mod,
        .linkage = .static,
    });
    b.installArtifact(hal_core);

    const sys_mod = b.createModule(.{
        .root_source_file = b.path("src/sys.zig"),
        .target = target,
        .optimize = optimize,
    });
    const sys_utils = b.addLibrary(.{
        .name = "sys_utils",
        .root_module = sys_mod,
        .linkage = .static,
    });
    b.installArtifact(sys_utils);

    const ffi_mod = b.createModule(.{
        .root_source_file = b.path("src/ffi.zig"),
        .target = target,
        .optimize = optimize,
    });
    const ffi_bridge = b.addLibrary(.{
        .name = "ffi_bridge",
        .root_module = ffi_mod,
        .linkage = .static,
    });
    b.installArtifact(ffi_bridge);

    const test_mod = b.createModule(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
        .imports = &.{
            .{ .name = "sys", .module = sys_mod },
            .{ .name = "ffi", .module = ffi_mod },
            .{ .name = "hal", .module = hal_mod },
        },
    });
    const tests = b.addTest(.{
        .root_module = test_mod,
    });
    const run_tests = b.addRunArtifact(tests);
    const test_step = b.step("test", "Run Zig unit tests");
    test_step.dependOn(&run_tests.step);
}
