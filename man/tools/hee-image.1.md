% HEE-IMAGE(1) | HEE Tools

# NAME

hee-image - inspect and flash images onto devices, safely.

# SYNOPSIS

    hee image [-h] {list,check,flash,make} ...
      hee image list                 -- flashable targets: cards and ttyUSB serial
      hee image check DEVICE         -- deep pre-flight on one block device
                                        e.g. hee image check /dev/mmcblk0
      hee image flash --image FILE --device DEVICE [--yes] [--no-verify]
                                     -- flash a .img or .img.xz to a card, then verify
      hee image make --size SIZE [PATH] [--pattern zero|random]
                                     -- make a scratch image (default random) for
                                        testing flash, e.g. --size 1M (K/M/G suffix)

    flash:
      Refuses any protected device (system mount, fixed sata/nvme, the root disk,
      read-only) or one too small for the image. Unmounts the target's own
      partitions first. Interactively it asks you to type the device path back;
      --yes bypasses that for automation. Without a tty and without --yes it prints
      the plan and writes nothing. Writes with `dd conv=fsync` (root, via sudo) and,
      unless --no-verify, reads the written region back and compares its sha256 to
      the decompressed image.

    Planned (own PRs, tracked as issues): serial/ttyUSB firmware flash routed to
    esptool; `stick` (fold in installer/debian/build-stick, the Ventoy Debian
    installer); `docker` image build/save/load.

    Env:
      HEE_SD_LSBLK   override the lsblk binary (testing)

    Exit: Nagios -- 0 OK, 1 WARNING (a refusal or a dry-run plan), 2 CRITICAL
          (a write/verify/read failed), 3 UNKNOWN (environment/usage).

# DESCRIPTION


    positional arguments:
      {list,check,flash,make}
        list                flashable targets: cards and ttyUSB serial
        check               deep pre-flight on one block device
        flash               flash an image onto a card, then verify
        make                make a scratch test image

    options:
      -h, --help            show this help message and exit

    hee-image -- inspect and flash images onto devices, safely.

    One verb for the fleet's "write an image to a thing" jobs. Today it does the
    block-device domain: flash a TCOS Pi image (installer/pi, e.g.
    tcos-pi-hera-*.img.xz) onto an SD/MMC or USB card, with the device safety that
    makes it a tool and not a bare `dd` -- it refuses to write anything that carries
    a system mountpoint (/, /boot...), is a fixed internal disk (sata/nvme), or
    backs the running root, so a mistyped device can never clobber the machine you
    build on. The `RM` (removable) flag is deliberately NOT trusted alone: a
    laptop's built-in SD reader shows RM=0 just like the NVMe system disk (measured
    on flippy: mmcblk0). The safe discriminator is transport (mmc/usb) + hotplug +
    "hosts no system mount" + "is not the root disk", stacked so any one failing
    refuses the write.
