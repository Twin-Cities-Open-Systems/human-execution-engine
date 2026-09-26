% HEE-IMAGE(1) | HEE Tools

# NAME

hee-image - inspect and flash images onto devices, safely.

# SYNOPSIS

    hee image [-h] {list,check,flash,build,make} ...
      hee image list                 -- flashable targets: cards and ttyUSB serial
      hee image check DEVICE         -- deep pre-flight on one block device
                                        e.g. hee image check /dev/mmcblk0
      hee image flash --image FILE --device DEVICE [--yes] [--no-verify]
                                     -- flash a .img or .img.xz to a card, then verify
      hee image flash --image FILE.bin --device /dev/ttyUSB0 [--chip esp32|esp8266]
                      [--offset 0x0] [--erase] [--yes]
                                     -- write a merged firmware image to a board
      hee image build --firmware espectre --chip esp32 [--repo DIR]
                      [--ota-channel release|preview|develop] [--clean] [--out DIR]
                      [--dry-run]    -- build ESPectre Native and merge it into one
                                        flashable .bin, named by chip and version
      hee image make --size SIZE [PATH] [--pattern zero|random]
                                     -- make a scratch image (default random) for
                                        testing flash, e.g. --size 1M (K/M/G suffix)

    flash (card):
      Refuses any protected device (system mount, fixed sata/nvme, the root disk,
      read-only) or one too small for the image. Unmounts the target's own
      partitions first. Interactively it asks you to type the device path back;
      --yes bypasses that for automation. Without a tty and without --yes it prints
      the plan and writes nothing. Writes with `dd conv=fsync` (root, via sudo) and,
      unless --no-verify, reads the written region back and compares its sha256 to
      the decompressed image.

    flash (serial):
      The device must be one `hee image list` shows as SERIAL. esptool first reads
      the board's MAC (the inventory's stableid) so you confirm the board, not just
      the port; a port another process holds (a monitor) fails here, before any
      write, with the fuser hint. Classic ESP32 is driven at 115200: esptool 5.3+
      loses it at 460800 during the stub's SFDP probe (ESPectre measured this;
      esptool_runner.py). The write is esptool's own, which hashes every region
      after writing; --no-verify has no meaning here and is ignored. --erase wipes
      the whole flash first (NVS, Wi-Fi credentials, OTA data) -- use it for a
      board changing firmware families, not for an update.
      --chip esp8266 flashes the fleet's NodeMCU soil/weather nodes, whose
      arduino-cli build is a single image at 0x0 (esp32/firmware/soil-weather-node);
      it runs at 460800 like every non-classic-esp32 chip. `build` stays esp32-only:
      it drives ESPectre Native, which is ESP-IDF.

    build:
      Runs the firmware's own CLI (`./espectre native build`, in its checkout, with
      the shared ESP-IDF from /etc/profile.d/esp-idf.sh when the shell did not read
      it) and then merges bootloader, partition table, OTA data and app into ONE
      image at offset 0, so flash needs one file and one offset. The name carries
      the chip and the checkout's `git describe`, the output line carries the
      sha256: that pair is what an inventory record's firmware/flash_image_sha256
      fields want. A lab build with Wi-Fi baked in is the checkout's own
      app/sdkconfig.wifi overlay (fleet-ops esp32/bin/render-secrets.sh
      --format sdkconfig); this verb does not touch secrets.

    Planned (own PRs, tracked as issues): `stick` (fold in installer/debian/
    build-stick, the Ventoy Debian installer); `docker` image build/save/load.

    Env:
      HEE_SD_LSBLK    override the lsblk binary (testing)
      ESPECTRE_REPO   the ESPectre checkout (default ~/git/espectre)
      IDF_PATH, IDF_TOOLS_PATH   an active ESP-IDF; else read from
                      /etc/profile.d/esp-idf.sh (fleet-ops esp32/bin/install-esp-idf.sh)


# DESCRIPTION


    positional arguments:
      {list,check,flash,build,make}
        list                flashable targets: cards and ttyUSB serial
        check               deep pre-flight on one block device
        flash               flash an image onto a card or a serial board, then
                            verify
        build               build a firmware and merge it into one flashable .bin
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

    The second domain is firmware over serial: build an ESP32 image from a firmware
    checkout and write it to a board on /dev/ttyUSB*, through esptool, so the fleet
    has one verb for "put an image on a thing" whether the thing is an SD card or a
    microcontroller. Same shape: the plan first, a typed confirmation, a sha256 the
    inventory record can point at.


# EXAMPLES

      $ hee image build --firmware espectre --chip esp32 --dry-run   # ci
      $ hee image build --firmware espectre --chip esp32 --ota-channel develop --out /srv/tcos/esp32/firmware
      $ hee image flash --image espectre-native-esp32-v3.0.0.bin --device /dev/ttyUSB0
      $ hee image flash --image soil-weather-node.ino.bin --device /dev/ttyUSB0 --chip esp8266

    Exit: Nagios -- 0 OK, 1 WARNING (a refusal or a dry-run plan), 2 CRITICAL
          (a write/verify/read failed), 3 UNKNOWN (environment/usage).
