const std = @import("std");

pub fn swapEndianU16(val: u16) u16 {
    return @byteSwap(val);
}

pub fn swapEndianU32(val: u32) u32 {
    return @byteSwap(val);
}

pub fn swapEndianU64(val: u64) u64 {
    return @byteSwap(val);
}

pub fn isBitSet(val: u32, bit: u3) bool {
    return (val >> bit) & 1 == 1;
}

pub fn setBit(val: u32, bit: u3) u32 {
    return val | (@as(u32, 1) << bit);
}

pub fn clearBit(val: u32, bit: u3) u32 {
    return val & ~(@as(u32, 1) << bit);
}

pub fn toggleBit(val: u32, bit: u3) u32 {
    return val ^ (@as(u32, 1) << bit);
}

pub fn countBits(val: u32) u3 {
    return @popCount(val);
}

pub fn alignUp(value: usize, alignment: usize) usize {
    return (value + alignment - 1) / alignment * alignment;
}

pub fn alignDown(value: usize, alignment: usize) usize {
    return value / alignment * alignment;
}

pub fn mmioRead8(base: [*]volatile u8, offset: usize) u8 {
    return base[offset];
}

pub fn mmioRead16(base: [*]volatile u16, offset: usize) u16 {
    return base[offset];
}

pub fn mmioRead32(base: [*]volatile u32, offset: usize) u32 {
    return base[offset];
}

pub fn mmioWrite8(base: [*]volatile u8, offset: usize, value: u8) void {
    base[offset] = value;
}

pub fn mmioWrite16(base: [*]volatile u16, offset: usize, value: u16) void {
    base[offset] = value;
}

pub fn mmioWrite32(base: [*]volatile u32, offset: usize, value: u32) void {
    base[offset] = value;
}

pub fn crc32(data: []const u8) u32 {
    var crc: u32 = 0xFFFFFFFF;
    for (data) |byte| {
        crc ^= byte;
        var i: u5 = 0;
        while (i < 8) : (i += 1) {
            if (crc & 1 != 0) {
                crc = (crc >> 1) ^ 0xEDB88320;
            } else {
                crc = crc >> 1;
            }
        }
    }
    return ~crc;
}

pub fn delayCycles(cycles: u64) void {
    _ = cycles;
}
