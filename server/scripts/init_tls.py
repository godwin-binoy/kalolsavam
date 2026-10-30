#!/usr/bin/env python3
"""Generate a local CA + server certificate for the venue LAN.

Creates server/certs/ca.pem (distribute to staff devices via QR/out-of-band)
and server/certs/server.pem|server.key valid for SERVER_HOST's IP.
Never commit the certs directory (gitignored).
"""
from __future__ import annotations

import datetime as dt
import ipaddress
import socket
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.config import Config  # noqa: E402


def gen() -> None:
    cfg = Config()
    cert_dir = Path(cfg.tls_cert).parent
    cert_dir.mkdir(parents=True, exist_ok=True)

    ca_key = ec.generate_private_key(ec.SECP256R1())
    now = dt.datetime.now(dt.timezone.utc)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,
                                            "Kalolsavam Local CA")])
    ca_cert = (x509.CertificateBuilder()
               .subject_name(ca_name).issuer_name(ca_name)
               .public_key(ca_key.public_key())
               .serial_number(x509.random_serial_number())
               .not_valid_before(now - dt.timedelta(days=1))
               .not_valid_after(now + dt.timedelta(days=825))
               .add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
               .sign(ca_key, hashes.SHA256()))

    srv_key = ec.generate_private_key(ec.SECP256R1())
    hosts = [ipaddress.ip_address(cfg.host)] if cfg.host not in ("0.0.0.0", "::") \
        else [ipaddress.ip_address("127.0.0.1")]
    san = x509.SubjectAlternativeName(
        [x509.IPAddress(ip) for ip in hosts] +
        [x509.DNSName("localhost"), x509.DNSName(socket.gethostname())])
    srv_cert = (x509.CertificateBuilder()
                .subject_name(x509.Name([x509.NameAttribute(
                    NameOID.COMMON_NAME, str(hosts[0]))]))
                .issuer_name(ca_name)
                .public_key(srv_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - dt.timedelta(days=1))
                .not_valid_after(now + dt.timedelta(days=398))
                .add_extension(san, critical=False)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
                .sign(ca_key, hashes.SHA256()))

    (cert_dir / "ca.pem").write_bytes(ca_cert.public_bytes(
        serialization.Encoding.PEM))
    Path(cfg.tls_cert).write_bytes(srv_cert.public_bytes(
        serialization.Encoding.PEM))
    key_path = Path(cfg.tls_key)
    key_path.write_bytes(srv_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()))
    key_path.chmod(0o600)
    print(f"Wrote {cert_dir/'ca.pem'}, {cfg.tls_cert}, {cfg.tls_key}")
    print("Distribute ca.pem to staff devices (QR or USB) and trust it; "
          "then dashboards load without browser warnings.")


if __name__ == "__main__":
    gen()
