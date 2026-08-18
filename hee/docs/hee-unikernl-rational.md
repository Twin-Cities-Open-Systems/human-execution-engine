# Thesis

This standalone C source file implements the architectural blueprint and direct bare-metal configuration parameters for compiling a stateless Scheme-embedded unikernel designed to execute as a hardware-level logical gate under a local Proxmox Virtual Environment (PVE) KVM hypervisor.

## Architectural Rationale & Low-Abstraction Optimization
This bare-metal source file design goes "further left" by removing the operating system entirely and compiling your logic directly into an x86 machine image.

   1. Direct Hypervisor Execution (Zero OS Overhead): The .multiboot data block at the top of the script signals straight to Proxmox VE’s underlying QEMU instances that this binary requires no disk partitions, no filesystems, and no bootloaders. Proxmox loads the compiled machine code instructions directly into the physical memory slice allocated to the VM, jumping straight to hee_unikernel_main.
   2. Erazing Context Switching and Bloat: A standard Linux operating system alternates CPU execution between unprivileged "user-space" (where interpreters live) and privileged "kernel-space" (where network sockets and hardware interactions are handled). This unikernel file erases that dividing boundary entirely. Your Scheme cell structures, raw text tracking routines, and x86 I/O assembly primitives (outb / inb) reside entirely in a single, unified, ring-0 privileged space.
   3. The 4MB Memory Freeze: Because there are no multi-user background daemons, cron facilities, or system logging services, the system memory footprint is locked to the size of your static arrays (configured above at exactly 4 megabytes). The heap pointer is calculated linearly, which completely prevents memory leaks and guarantees that performance remains constant over years of continuous fleet deployment.

To deploy this in your PVE architecture, compile this file via standard gcc with the flags -nostdlib -fno-builtin -m32 to strip the standard glibc libraries, then specify the path to the resulting binary directly inside your Proxmox virtual machine target configuration file via the kernel: declaration.


