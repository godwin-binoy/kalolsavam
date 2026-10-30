/* SRP-6a client for the Kalolsavam dashboards.
 * Uses Web Crypto SHA-256 + native BigInt. The password NEVER leaves this
 * device: we only send A = g^a mod N and the proof M1.
 * MUST match server/auth.py (RFC 5054 2048-bit group, x = H(s | H(I ":" P))). */
(function () {
  'use strict';

  var N_HEX =
    'AC6BCA4F50455F7CCD71C6B8CEB40E31F8A3E1CC654C7BF8E77FCC29B48D58FE' +
    'A3B14DC3F2C3B5687482C875CEF96B0880B9E27682BDA698E3E3C77B676A6D93' +
    '100F0753EDAF79BA75B3757EC6FA4C5B09FF3BBE37B1A25A9FDDB052C1F870FC' +
    '26E3418EB281C0DE6B51F9B38423BA867CCBE0EA487E4ACC7E6C356DE88768A9' +
    'DD04C5F382B4C301C6DA42381D641A863902BF00696D3570A0123C5CE1F9B808' +
    'D3780135BADA78E9B1AE508A989C3D1DBC9F4B1E46F8708D96DEF587E2EF07CB';

  function hexToBytes(h) {
    if (h.length % 2) h = '0' + h;
    var out = new Uint8Array(h.length / 2);
    for (var i = 0; i < out.length; i++) {
      out[i] = parseInt(h.substr(i * 2, 2), 16);
    }
    return out;
  }

  function bytesToHex(b) {
    var s = '';
    for (var i = 0; i < b.length; i++) s += b[i].toString(16).padStart(2, '0');
    return s;
  }

  function bigToBytes(n) {
    var h = n.toString(16);
    if (h.length % 2) h = '0' + h;
    return hexToBytes(h);
  }

  // fixed-width big-endian byte encoding used by the SRP hash inputs
  function padBig(n, width) {
    var b = bigToBytes(n);
    var out = new Uint8Array(width);
    out.set(b, width - b.length);
    return out;
  }

  async function sha256() {
    var parts = [];
    for (var i = 0; i < arguments.length; i++) {
      var p = arguments[i];
      if (typeof p === 'string') p = new TextEncoder().encode(p);
      parts.push(p);
    }
    var buf = await crypto.subtle.digest('SHA-256', concat(parts));
    return new Uint8Array(buf);
  }

  function concat(parts) {
    var len = parts.reduce(function (a, p) { return a + p.length; }, 0);
    var out = new Uint8Array(len), o = 0;
    for (var i = 0; i < parts.length; i++) { out.set(parts[i], o); o += parts[i].length; }
    return out;
  }

  async function derive(username, password, saltHex) {
    var inner = await sha256(username + ':' + password);
    var x = await sha256(hexToBytes(saltHex), inner);
    return BigInt('0x' + bytesToHex(x));
  }

  async function makeVerifier(username, password, saltHex) {
    var N = BigInt('0x' + N_HEX), g = 2n;
    var x = await derive(username, password, saltHex);
    return modPow(g, x, N).toString(16);
  }

  function modPow(base, exp, mod) {
    base %= mod; var res = 1n;
    while (exp > 0n) {
      if (exp & 1n) res = (res * base) % mod;
      base = (base * base) % mod;
      exp >>= 1n;
    }
    return res;
  }

  function randomBelow(mod) {
    var nbytes = (mod.toString(16).length + 1) >> 1;
    var buf = new Uint8Array(nbytes);
    crypto.getRandomValues(buf);
    var v = BigInt('0x' + (bytesToHex(buf) || '0')) % (mod - 1n);
    return v + 1n;
  }

  async function kValue(N, g, padLen) {
    var h = await sha256(padBig(N, padLen), padBig(g, padLen));
    return BigInt('0x' + bytesToHex(h));
  }

  /* Full login exchange. Returns {salt, A_hex, M1_hex, S, B} — the caller
   * posts challenge/verify and then confirms server mutual auth with M2. */
  async function clientStart(username, password) {
    var N = BigInt('0x' + N_HEX), g = 2n;
    var padLen = Math.ceil(N.toString(16).length / 2);
    var a = randomBelow(N);
    var A = modPow(g, a, N);
    return { username: username, password: password, a: a, A: A,
             A_hex: A.toString(16), padLen: padLen };
  }

  async function clientFinish(st, saltHex, B_hex) {
    var N = BigInt('0x' + N_HEX), g = 2n;
    var B = BigInt('0x' + B_hex);
    if (B % N === 0n) throw new Error('invalid server ephemeral');
    var k = await kValue(N, g, st.padLen);
    var x = await derive(st.username, st.password, saltHex);
    var u = BigInt('0x' + bytesToHex(await sha256(padBig(st.A, st.padLen), padBig(B, st.padLen))));
    if (u === 0n) throw new Error('invalid u');
    var base = (B - k * modPow(g, x, N)) % N;
    if (base < 0n) base += N;
    var S = modPow(base, st.a.add ? st.a : st.a, N); // placeholder replaced below
    S = modPow(base, st.a + u * x, N);
    var K = await sha256(padBig(S, st.padLen));

    var hN = await sha256(padBig(N, st.padLen));
    var hg = await sha256(padBig(g, st.padLen));
    var pad = new Uint8Array(hN.length);
    for (var i = 0; i < hN.length; i++) pad[i] = hN[i] ^ hg[i];
    var hU = await sha256(st.username);
    var M1 = await sha256(pad, hU, hexToBytes(saltHex),
                         padBig(st.A, st.padLen), padBig(B, st.padLen), K);
    var M2 = await sha256(padBig(st.A, st.padLen), M1, K);
    return { M1_hex: bytesToHex(M1), M2_expected_hex: bytesToHex(M2) };
  }

  window.KalSRP = {
    clientStart: clientStart,
    clientFinish: clientFinish,
    makeVerifier: makeVerifier
  };
})();
