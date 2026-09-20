/* qr.js -- read a QR code out of a picture, however this browser can.
 *
 * section: 3
 *
 * WHY THIS EXISTS
 *   The platform has a decoder -- `BarcodeDetector` -- and on Android Chrome
 *   it is the right one to use: it is hardware-accelerated, costs no bytes,
 *   and is maintained by someone else. It is also, measured on flippy
 *   2026-09-19 in Chrome 153 on Debian 13 over HTTPS:
 *
 *       typeof BarcodeDetector  ->  "undefined"
 *
 *   It does not exist in desktop Linux Chrome, and it does not exist in
 *   Firefox at all. So a page that scans only when `BarcodeDetector` is
 *   present is a page that does not scan on the kiosk at the counter, which
 *   runs Firefox. A JavaScript decoder is not a nicety here; without one the
 *   feature is absent on the machine it was asked for.
 *
 *   Neither is a page allowed to care which of the two it got. That is this
 *   file's whole job: ONE entry point, the platform preferred when it is
 *   really there, the vendored decoder underneath it when it is not.
 *
 * THE API
 *
 *   heeQrScan(source, [opts]) -> Promise<string|null>
 *       The entry point. `source` is a <video>, a <canvas>, an <img>, an
 *       ImageBitmap or an ImageData. Resolves to the decoded text, or null
 *       when this frame held no readable QR -- null is the ordinary answer
 *       while a camera is still being pointed, not an error. It REJECTS only
 *       when there is no decoder at all (see heeQrAvailable).
 *
 *   heeQrDecode(imageData) -> string|null
 *       The vendored decoder alone, synchronous, no platform path. For a
 *       caller that already has pixels and wants a straight answer -- a
 *       test, or decoding a PNG that was never on a camera.
 *
 *   heeQrAvailable() -> boolean
 *       Can anything here decode at all? False only when qr-jsqr.js was not
 *       loaded AND the platform has no BarcodeDetector. A caller that gets
 *       false should say so and keep its manual path open, never hide it.
 *
 *   heeQrBackend() -> "platform" | "vendored" | "none" | "unknown"
 *       Which one actually answered. "unknown" until the first heeQrScan()
 *       resolves the question, because the platform probe is async. Report
 *       it, do not branch on it.
 *
 * WHAT IT DOES NOT DO
 *   No camera. No getUserMedia, no permission prompt, no <video> of its own,
 *   no UI. A decoder that also owned the camera could not be tested without
 *   one, and every page wants a different camera UI. Pixels in, text out.
 *
 * DEPENDENCIES
 *   `library/js/qr-jsqr.js` (jsQR 1.4.0, Apache-2.0, vendored -- see
 *   library/js/UPSTREAM.md) must be loaded BEFORE this file for the fallback
 *   to exist. Everything still loads and runs without it; heeQrAvailable()
 *   then reports what a browser with no BarcodeDetector actually has, which
 *   is nothing.
 *
 *   Zero other dependencies. No build step. Does nothing until called.
 */
(function (window, document) {
  "use strict";

  /* The platform probe is asynchronous (getSupportedFormats() returns a
   * promise), so it is run once and its answer memoized. Three states:
   * null = never asked, a promise = asking, and the resolved value is a
   * BarcodeDetector instance or false. */
  var platformProbe = null;
  var backend = "unknown";

  /* One canvas for the life of the page. A new one per frame is a new GPU
   * surface per frame, and at 4 frames a second that is what makes a scan
   * loop heat a laptop. */
  var scratch = null;
  var scratchCtx = null;

  /* Above this, the long side of a frame is scaled down before decoding.
   * A phone camera hands over 1920x1080 or more; jsQR is O(pixels) and a
   * scan loop runs this several times a second. 1280 keeps a typical QR's
   * modules several pixels wide, which is what the decoder needs, while
   * bounding the work. Pass {maxSide: 0} to turn scaling off entirely. */
  var DEFAULT_MAX_SIDE = 1280;

  function isImageData(x) {
    return !!x && typeof x === "object" &&
      typeof x.width === "number" && typeof x.height === "number" &&
      !!x.data && typeof x.data.length === "number";
  }

  /* The natural pixel size of a source, which is NOT its CSS size: a <video>
   * laid out 320px wide still decodes at videoWidth. Returns [0, 0] for a
   * source with nothing in it yet -- a <video> before the first frame has
   * arrived, which is the normal state for the first few hundred ms after
   * play() and must not be treated as a failure. */
  function sourceSize(source) {
    if (!source) { return [0, 0]; }
    if (isImageData(source)) { return [source.width, source.height]; }
    var w = source.videoWidth || source.naturalWidth || source.width || 0;
    var h = source.videoHeight || source.naturalHeight || source.height || 0;
    return [w, h];
  }

  function ensureScratch() {
    if (scratch) { return true; }
    if (!document || !document.createElement) { return false; }
    scratch = document.createElement("canvas");
    /* willReadFrequently: this context is read back with getImageData on
     * every single frame, which is the one access pattern the GPU-backed
     * default is worst at. Chrome warns about it in the console otherwise. */
    try {
      scratchCtx = scratch.getContext("2d", { willReadFrequently: true });
    } catch (e) {
      scratchCtx = null;
    }
    if (!scratchCtx) {
      try { scratchCtx = scratch.getContext("2d"); } catch (e2) { scratchCtx = null; }
    }
    return !!scratchCtx;
  }

  /* source -> ImageData, or null when there is nothing to read yet. */
  function toImageData(source, maxSide) {
    if (isImageData(source)) { return source; }
    var size = sourceSize(source);
    var w = size[0];
    var h = size[1];
    if (!w || !h) { return null; }

    var scale = 1;
    if (maxSide && Math.max(w, h) > maxSide) { scale = maxSide / Math.max(w, h); }
    var dw = Math.max(1, Math.round(w * scale));
    var dh = Math.max(1, Math.round(h * scale));

    if (!ensureScratch()) { return null; }
    if (scratch.width !== dw) { scratch.width = dw; }
    if (scratch.height !== dh) { scratch.height = dh; }

    try {
      scratchCtx.drawImage(source, 0, 0, dw, dh);
      return scratchCtx.getImageData(0, 0, dw, dh);
    } catch (e) {
      /* A cross-origin <img> taints the canvas and getImageData throws a
       * SecurityError. Nothing here can fix that, and a thrown exception
       * mid-scan-loop would look like a decoder bug, so it reads as "no QR
       * in this frame" and the caller keeps going. */
      return null;
    }
  }

  /* ---- the vendored decoder ------------------------------------------- */

  function haveVendored() {
    return typeof window.jsQR === "function";
  }

  /* heeQrDecode -- pixels in, text out, synchronously. null when this image
   * holds no QR this decoder can read.
   *
   * inversionAttempts "attemptBoth" is jsQR's own default and is kept: a QR
   * printed light-on-dark (a receipt in dark mode, a phone screen) decodes
   * only on the inverted pass, and at counter distances that happens. It
   * costs a second pass only on frames that failed the first, which are
   * exactly the frames where nothing else is happening. */
  function heeQrDecode(imageData, opts) {
    if (!haveVendored()) { return null; }
    if (!isImageData(imageData)) { return null; }
    var options = opts || {};
    var result;
    try {
      result = window.jsQR(imageData.data, imageData.width, imageData.height, {
        inversionAttempts: options.inversionAttempts || "attemptBoth"
      });
    } catch (e) {
      /* jsQR throwing on a malformed frame is a bug in jsQR, not an answer
       * this page can act on; it reads as "nothing here". */
      return null;
    }
    if (!result) { return null; }
    /* jsQR returns "" for a QR whose payload really is empty. That is a
     * decode, but it is not something a caller can use, so it reads as no
     * decode rather than as an empty success that silently fills a field. */
    return result.data ? result.data : null;
  }

  /* ---- the platform decoder -------------------------------------------- */

  /* Resolves to a BarcodeDetector instance that really does qr_code, or to
   * false. Both "the constructor is missing" and "the constructor is there
   * but qr_code is not among the supported formats" end at false -- the
   * second really happens, on browsers that ship the API backed by a
   * platform library with a narrower format list. */
  function probePlatform() {
    if (platformProbe) { return platformProbe; }
    platformProbe = new Promise(function (resolve) {
      var Ctor = window.BarcodeDetector;
      if (typeof Ctor !== "function") { resolve(false); return; }
      var formats;
      try {
        formats = typeof Ctor.getSupportedFormats === "function"
          ? Ctor.getSupportedFormats() : null;
      } catch (e) {
        resolve(false);
        return;
      }
      Promise.resolve(formats).then(function (list) {
        if (list && list.indexOf && list.indexOf("qr_code") === -1) {
          resolve(false);
          return;
        }
        try {
          resolve(new Ctor({ formats: ["qr_code"] }));
        } catch (e) {
          resolve(false);
        }
      }, function () {
        resolve(false);
      });
    });
    return platformProbe;
  }

  /* ---- the entry point -------------------------------------------------- */

  function heeQrAvailable() {
    return haveVendored() || typeof window.BarcodeDetector === "function";
  }

  function heeQrBackend() {
    return backend;
  }

  function vendoredScan(source, maxSide, opts) {
    var pixels = toImageData(source, maxSide);
    if (!pixels) { return null; }
    var text = heeQrDecode(pixels, opts);
    if (text !== null) { backend = "vendored"; }
    return text;
  }

  /* heeQrScan -- the one call a page should make.
   *
   * Resolving to null is the ordinary case: a camera pointed at a counter
   * top produces frames with no QR in them several times a second, and a
   * rejected promise per frame would be indistinguishable from the decoder
   * being broken. It rejects for exactly one reason -- there is no decoder
   * on this page at all -- because that one a caller must not paper over.
   *
   * A platform detector that throws is not retried. detect() failing once
   * (a detector wedged by a backgrounded tab, a platform library that went
   * away) fails every frame after it too, and falling back permanently to
   * the vendored decoder is both cheaper and quieter than logging the same
   * exception four times a second forever. */
  function heeQrScan(source, opts) {
    var options = opts || {};
    var maxSide = options.maxSide === undefined ? DEFAULT_MAX_SIDE : options.maxSide;

    if (!heeQrAvailable()) {
      backend = "none";
      return Promise.reject(new Error(
        "no QR decoder on this page: qr-jsqr.js is not loaded and this browser has no BarcodeDetector"
      ));
    }

    var size = sourceSize(source);
    if (!size[0] || !size[1]) {
      /* Nothing has been painted yet. Not an error, not a decode. */
      return Promise.resolve(null);
    }

    if (options.backend === "vendored" || !window.BarcodeDetector) {
      if (!haveVendored()) {
        backend = "none";
        return Promise.reject(new Error("qr-jsqr.js is not loaded, so there is no vendored decoder"));
      }
      backend = "vendored";
      return Promise.resolve(vendoredScan(source, maxSide, options));
    }

    return probePlatform().then(function (detector) {
      if (!detector) {
        if (!haveVendored()) {
          backend = "none";
          throw new Error(
            "this browser has no working BarcodeDetector and qr-jsqr.js is not loaded"
          );
        }
        backend = "vendored";
        return vendoredScan(source, maxSide, options);
      }
      backend = "platform";
      /* ImageData is an ImageBitmapSource, so it is handed to detect()
       * as-is; everything else the platform takes directly too. */
      return detector.detect(source).then(function (codes) {
        if (!codes || codes.length === 0) { return null; }
        var value = codes[0].rawValue;
        return value ? value : null;
      }, function () {
        /* Burned for the rest of the page's life, on purpose -- see above. */
        platformProbe = Promise.resolve(false);
        if (!haveVendored()) {
          backend = "none";
          throw new Error("BarcodeDetector failed and there is no vendored decoder to fall back to");
        }
        backend = "vendored";
        return vendoredScan(source, maxSide, options);
      });
    });
  }

  window.heeQrScan = heeQrScan;
  window.heeQrDecode = heeQrDecode;
  window.heeQrAvailable = heeQrAvailable;
  window.heeQrBackend = heeQrBackend;

  /* The namespace the rest of this directory publishes under, for a caller
   * that would rather not read four globals. */
  window.TC = window.TC || {};
  window.TC.qr = {
    scan: heeQrScan,
    decode: heeQrDecode,
    available: heeQrAvailable,
    backend: heeQrBackend
  };
})(window, document);
