---
title: "Chain devlog 1: build system"
---

This is the first devlog of a series where I'll be writing (well, rewriting) chain, a modern kernel and OS focused on simplicity and first principles.

The truth is that chain *kind of* already exists. It was a personal project that I had been developing for a while. It was really useful as a learning experience, as I did a bit of everything, even things I had never done before, like PCI. However, it eventually got to the point where early design decisions made further development harder. The most important ones are:
- No kernel multithreading
- Really bad scheduler implementation
- Extremely verbose filesystem APIs
- Tied to the limine bootloader
- Really bad LAPIC and IOAPIC implementation
- Really bad PS/2 implementation
- Too many "placeholders". Examples:
  - PS/2 keyboard waiting for a USB implementation
  - All SMP (except the main one) were halted
- Bad virtual memory management made DMA difficult

I recently decided to abandon the project codebase and start from scratch. However, There are some design decisions I do want to keep, namely:
- Microkernel design
- Everything is a file
- Everything in Zig

We'll go step by step. The first thing should be the build system.

# Barebones `build.zig`

We'll start by writing the actual `build.zig` file.

```zig
pub fn build(b: *std.Build) void {
    // ...
}
```

The first thing we need is the build target. We need to add and remove some features, so we'll do the query in a separate function.

```zig
fn getTarget(b: *std.Build, arch: std.Target.Cpu.Arch) std.Build.ResolvedTarget {
    const query: std.Target.Query = .{
        .cpu_arch = arch,
        .os_tag = .freestanding,
        .abi = .none,
        .cpu_features_add = switch (arch) {
            .x86_64 => std.Target.x86.featureSet(&.{.soft_float}),
            else => @panic("unsupported architecture"),
        },
        .cpu_features_sub = switch (arch) {
            .x86_64 => std.Target.x86.featureSet(&.{ .mmx, .sse, .sse2, .avx, .avx2 }),
            else => @panic("unsupported architecture"),
        },
    };

    return b.resolveTargetQuery(query);
}
```

Then, in the `build` function we can call it to get the target. We can also get the optimization mode:

```zig
const optimize = b.standardOptimizeOption(.{ .preferred_optimize_mode = .ReleaseSmall });
const kernel_target = getTarget(b, .x86_64);
```

Zig adds the `install` and `uninstall` steps by default. It's generally a good practice to keep those, but for a kernel it doesn't make much sense. We'll remove them:

```zig
b.top_level_steps.clearRetainingCapacity();
```

Then we create the kernel compile step, and make it the default
```zig
const kernel = b.addExecutable(.{
    .name = "chain",
    .target = kernel_target,
    .optimize = optimize,
    .root_source_file = b.path("kernel/src/main.zig"),
});
kernel.setLinkerScript(b.path("kernel/link-x86_64.ld"));

const kernel_step = b.step("kernel", "Build the kernel executable");
b.default_step = kernel_step;
kernel_step.dependOn(&b.addInstallArtifact(kernel, .{}).step);
```

This is enough to build the kernel ELF image. However, this is of course not bootable. We need a bootloader. At the same time, we don't want the kernel to be tied to a specific bootloder. What can we do? Bootstrap it!

## The stub image

We'll add a step to build what we'll call the *stub image*. It serves as a bootstrap from which to install chain. It is very similar to the [Arch linux](https://archlinux.org) *archiso*. It already contains a bootloader, bootloader configuration file, kernel image and initial ramdisk. Once you boot it, you can use chain to install chain on your desired drive. Part of that installation procedure is to create a boot partition with your favourite bootloader and bootloader configuration. Nice, isn't it?

We'll start by creating a directory using the handy `WriteFile` step. It will contain what we just described (except for the initial ramdisk, which isn't necessary yet).
```zig
const stub_iso_tree = b.addWriteFiles();
_ = stub_iso_tree.addCopyFile(kernel.getEmittedBin(), "kernel");
_ = stub_iso_tree.addCopyFile(b.path("limine.cfg"), "limine.cfg");
_ = stub_iso_tree.addCopyFile(b.dependency("limine", .{}).path("limine-uefi-cd.bin"), "limine-uefi-cd.bin");
```

We'll create the stub image bootloader (limine) configuration, `limine.cfg`:
```txt
:chain
    PROTOCOL=limine
    KERNEL_PATH=boot:///kernel
```

The stub image will be an ISO 9660 image, as it's very widespread. To create the image, we'll use a tool called `xorriso`. I'm not going to explain exactly how the ISO 9660 format works, you just need to know that the first 32KiB are unused. That area is called the *system area* and is usually used to store boot information, whether that is a GPT or MBR. We'll make the stub image UEFI-only, so we will put a GPT (GUID Partition Table) there.
```zig
const stub_iso_xorriso = b.addSystemCommand(&.{"xorriso"});
stub_iso_xorriso.addArgs(&.{ "-as", "mkisofs" });
stub_iso_xorriso.addArgs(&.{ "--efi-boot", "limine-uefi-cd.bin" });
stub_iso_xorriso.addArg("-efi-boot-part");
stub_iso_xorriso.addArg("--efi-boot-image");
stub_iso_xorriso.addArg("--protective-msdos-label");
stub_iso_xorriso.addDirectoryArg(stub_iso_tree.getDirectory());
stub_iso_xorriso.addArg("-o");
const stub_iso = stub_iso_xorriso.addOutputFileArg("chain_stub.iso");

const stub_iso_step = b.step("stub_iso", "Create a stub ISO, used to install chain");
stub_iso_step.dependOn(&b.addInstallFile(stub_iso, "chain_stub.iso").step);
```

And there we have our stub image!

We'll also create a convenient `qemu` step, which will run the stub image in QEMU.
```zig
const qemu = b.addSystemCommand(&.{"qemu-system-x86_64"});
qemu.addArg("-bios");
qemu.addFileArg(b.dependency("ovmf", .{}).path("RELEASEX64_OVMF.fd"));
qemu.addArg("-cdrom");
qemu.addFileArg(stub_iso);
qemu.addArgs(&.{ "-debugcon", "stdio" });

const qemu_step = b.step("qemu", "Run the stub ISO in QEMU");
qemu_step.dependOn(&qemu.step);
```

# Hello world
We have our build system ready to go. But we don't have a kernel! Okay, let's write a hello world... Wait! Where do we put the code?

## Source code structure
I spend way too much time thinking about the source code structure for my projects. The fact that a kernel has common and architectrure-specific parts doesn't make it easier. Over the years, I've decided that the structure I like the most is the following:
- `kernel`: everything strictly related to the kernel (no userspace code or tools in here)
  - `src`: the actual source code of the kernel (not everything kernel-related is code)
    - `arch/foo`: code specific to the `foo` architecture
- `tools`: host tools (e.g. initrd creation tool)
- `user`: everything strictly related to the userspace

## Entry point
We'll define `_start`, which will be the entry point. For now, we'll halt.
```zig
export fn _start() callconv(.C) noreturn {
    while (true) {}
}
```

## Linker script
The compiler (or rather, the linker) doesn't know how to arrange the compiled code and data into an ELF file. That's what linker scripts are for. When compiling normal applications we don't need to create a linker script, as the compiler will use the default one for the target you are compiling for. However, this doesn't work for a kernel. We need to write out own. I'm not going to explain every single line (it's not *that* important), but I will put it here either way:
```txt
TARGET(elf64-x86-64)
ENTRY(_start)

PHDRS {
    text PT_LOAD FLAGS((1 << 0) | (1 << 2)); /* r-x */
    rodata PT_LOAD FLAGS((1 << 2)); /* r-- */
    data PT_LOAD FLAGS((1 << 1) | (1 << 2)); /* rw- */
}

SECTIONS {
    . = 0xffffffff80000000;

    . = ALIGN(0x1000);

    .text : {
        *(.text)
        *(.text.*)
    } :text

    . = ALIGN(0x1000);

    .rodata : {
        *(.text)
        *(.text.*)
    } :rodata

    . = ALIGN(0x1000);

    .data : {
        *(.data)
        *(.data.*)
    } :data

    . = ALIGN(0x1000);

    .bss : {
        *(.bss)
        *(.bss.*)
        *(COMMON)
    } :data

    /DISCARD/ : {
        *(.eh_frame)
        *(.note)
        *(.note.*)
    }
}
```

Notice how we set `. = 0xffffffff80000000`. Let's say the compiler wants to perform a jump to another part of the code. It needs to know where in memory that code will end up. That's why we need to override the special `.` variable which is the current memory offset (the kernel is loaded at the higher half of virtual memory). We also modify that variable in order to align it to 4KiB pages (`0x1000` bytes) between sections.

## The actual hello world

If we run `zig build qemu` we'll see how it boots. That's not very impressive... Many emulators support something called the *E9 hack*. It's very simple: whatever you write into the port `0xE9` will be written to the *debugcon*. We can use a bit of inline assembly to write an `x`.
```zig
asm volatile (
    \\mov $'x', %al
    \\out %al, $0xe9
    ::: "al");
```

Run `zig build qemu` and... there it is!

---

With this, we can say we have the barebones of a kernel! You can follow the project on [github](https://github.com/os-chain/chain).
