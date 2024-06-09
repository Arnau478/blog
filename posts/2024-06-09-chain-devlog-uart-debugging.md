---
title: "Chain devlog 2: UART debugging"
---

In the [last devlog](chain-devlog-build-system.html) we set up the barebones for a kernel. We'll write a lot of bugs, so being able to debug the kernel should be our main priority.

When you have a normal application the simplest way of debugging is printing stuff. However, our kernel is not running under an OS, so we cannot simply "print to a terminal". One option would be to print to the screen, but that would require a lot of prior work (which we wouldn't be able to debug). It would also require, well, having a screen. There is a much better option that virtually all computers support: UART.

UART (**u**niversal **a**synchronous **r**eceiver/**t**ransmitter) is a very popular serial data protocol (in fact, it's sometimes called just "serial"). Most importantly, we can pass some flags to QEMU to print it in our terminal. Let's do that now, changing `debugcon` with `serial`:

```diff
- qemu.addArgs(&.{ "-debugcon", "stdio" });
+ qemu.addArgs(&.{ "-serial", "stdio" });
```

But how do we write to the UART? Well, get ready to write our first driver!

# UART driver

For x86_64 computers, we can talk to the UART chip (usually the *16550 UART*) via I/O ports. To do so, we need to use the assembly instructions `in` and `out`. We *could* write inline assembly blocks everywhere... But we can also have two small inline functions in `kernel/src/arch/x86_64/cpu.zig` that do so. Here are the 8-bit ones (`b` postfix):
```zig
pub inline fn inb(port: u16) u8 {
    return asm volatile ("inb %[port], %[result]"
        : [result] "={al}" (-> u8),
        : [port] "{dx}" (port),
    );
}

pub inline fn outb(port: u16, data: u8) void {
    asm volatile ("outb %[data], %[port]"
        :
        : [data] "{al}" (data),
          [port] "{dx}" (port),
    );
}
```

If you remember correctly, the "A" from UART stands for *asynchronous*. It means there's no clock signal that tells the receiver when a bit is sent. To make it work, both devices have to agree on a set speed. There are a few common speeds, which are multiples or divisors of a base frequency (or *baudrate*). For historical reasons, they're all multiples of 75. However, UART chips don't usually use 75 as its base frequency and use multiples of it. This is because getting a signal of double the frequency (multiplying the frequency) is much harder than getting one of half the frequency (dividing the frequency) in hardware. So chips have a base frequency from which they take **divisors**, not multiples. In the case of the *16550 UART* it's 115200. We'll abstract the concept of a speed:
```zig
pub const Speed = enum(usize) {
    pub const base = 115200;

    @"115200",
    @"57600",
    @"38400",
    @"19200",
    @"9600",
    @"4800",

    /// Get the numeric baudrate
    pub fn getBaudrate(self: Speed) usize {
        return switch (self) {
            inline else => |s| std.fmt.parseInt(usize, @tagName(s), 10) catch unreachable,
        };
    }

    /// From a set baudrate. Returns null if invalid.
    pub fn fromBaudrate(baudrate: usize) ?Speed {
        inline for (comptime std.enums.values(Speed)) |speed| {
            if (baudrate == speed.getBaudrate()) {
                return speed;
            }
        }

        // Invalid baudrate
        return null;
    }

    /// Get the clock divisor for a specific speed
    pub fn getDivisor(self: Speed) u16 {
        return @intCast(@divExact(base, self.getBaudrate()));
    }
};
```

We can access what we call *registers* via I/O ports. We have a different base address for each serial port, to which we add an offset to access a specific register. Some have a different meaning depending on whether you're reading it or writing it. Some also change meaning depending on the DLAB flag:
<table>
    <tr><th>Offset</th><th>DLAB</th><th>I/O Direction</th><th>Register                               </th></tr>
    <tr><td>0     </td><td>0   </td><td>Read         </td><td>Receive buffer                         </td></tr>
    <tr><td>0     </td><td>0   </td><td>Write        </td><td>Transmit buffer                        </td></tr>
    <tr><td>1     </td><td>0   </td><td>Read/Write   </td><td>Interrupt enable                       </td></tr>
    <tr><td>0     </td><td>1   </td><td>Read/Write   </td><td>Baudrate divisor least significant byte</td></tr>
    <tr><td>1     </td><td>1   </td><td>Read/Write   </td><td>Baudrate divisor most significant byte </td></tr>
    <tr><td>2     </td><td>-   </td><td>Read         </td><td>Interrupt identification               </td></tr>
    <tr><td>2     </td><td>-   </td><td>Write        </td><td>FIFO control register                  </td></tr>
    <tr><td>3     </td><td>-   </td><td>Read/Write   </td><td>Line control register                  </td></tr>
    <tr><td>4     </td><td>-   </td><td>Read/Write   </td><td>Modem control register                 </td></tr>
    <tr><td>5     </td><td>-   </td><td>Read         </td><td>Line status register                   </td></tr>
    <tr><td>6     </td><td>-   </td><td>Read         </td><td>Modem status register                  </td></tr>
    <tr><td>7     </td><td>-   </td><td>Read/Write   </td><td>Scratch register                       </td></tr>
</table>

## Initialization
The first thing we have to do is initialize the chip. This involves configuring a few things. We'll only configure the first serial port, which has the I/O port base `0x3F8`.
```zig
pub fn init(speed: Speed) void {
    switch (builtin.cpu.arch) {
        .x86_64 => {
            const cpu = @import("arch/x86_64/cpu.zig");

            // ...
        },
        else => unreachable,
    }
}
```

### Speed
We first have to configure the speed at which it will operate. Notice how both registers regarding the baudrate divisor are accessed with DLAB=1.
```zig
// Set the speed
cpu.outb(0x3F8 + 3, 0x80); // Enable DLAB
cpu.outb(0x3F8, @intCast(speed.getDivisor() >> 8));
cpu.outb(0x3F8, @truncate(speed.getDivisor()));
cpu.outb(0x3F8 + 3, 0x0); // Disable DLAB
```

### Bits, parity, stop bits, break control
99% of serial communications are 8 bits long, without parity, with one stop bit and no break control. We just make sure that's how the chip is configured.
```zig
cpu.outb(0x3F8 + 3, 0x03); // 8 bits, no parity, 1 stop bit, no break control
```

### FIFO
The FIFO queues probably contain garbage. We need to enable them and clear them.
```zig
cpu.outb(0x3F8 + 2, 0xc7); // FIFO enabled, clear both FIFOs, 14 bytes
```

### Modem
The modem is about how data is passed through the wires at low level. We'll set `DTR` and `RTS`. This one is not really necessary nor important, but we'll do it anyway.
```zig
cpu.outb(0x3F8 + 4, 0x03); // RTS, DTS
```

## Sending characters
We're ready to send characters now! To do so, we just have to write to the transmit buffer register. Easy, right? Well, there's a catch. When operating at low speeds it's easy to overflow the FIFO. We basically have to check whether the FIFO is empty before writing. The simplest way to do so is to halt until it's empty. It's not the perfect approach, but we can't do much better until we have interrupts working.
```zig
pub fn putc(char: u8) void {
    switch (builtin.cpu.arch) {
        .x86_64 => {
            const cpu = @import("arch/x86_64/cpu.zig");

            while (cpu.inb(0x3F8 + 5) & 0x20 == 0) {}
            cpu.outb(0x3F8, char);
        },
        else => unreachable,
    }
}
```

And that's it! We can write to the serial port.

# Logging system

Writing logs character-by-character is not something you'd want. Fortunately, the zig standard library logging system is very versatile and allows you to overwrite the low-level logging function. Then you can use all those features like scoped logs and log levels without effort. It really comes to how you want your logs printed. I wrote it in `debug.zig`, if you want to take a look in the repo.

Then you just have to do the following:
```zig
pub const std_options = .{
    .logFn = debug.logFn,
    .log_level = switch (builtin.mode) {
        .Debug => .debug,
        else => .info,
    },
};
```

# A new hello world

In the last post, our *hello world* was printing an `x` character. In this one we'll make it a proper *hello world*. We'll also restructure the `_start` function and create a panic handler:
```zig
pub fn panic(msg: []const u8, _: ?*std.builtin.StackTrace, _: ?usize) noreturn {
    log.err("*Panic*\n{s}", .{msg});

    while (true) {}
}

export fn _start() callconv(.C) noreturn {
    init() catch |err| switch (err) {
        error.OutOfMemory => @panic("Ran out of memory while initializing the kernel"),
    };

    while (true) {}
}

pub fn init() !void {
    uart.init(uart.Speed.fromBaudrate(9600).?);

    log.debug("Initializing", .{});
}
```

That's it! We've got a *proper* hello world (and most importantly, a UART driver).

---

You can follow the project on [github](https://github.com/os-chain/chain).
