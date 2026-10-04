# Test Keys

This folder contains test public/private key pairs for testing the TI CyberShield Toolkit.

## Keys

| Key File | Type | Size/Curve | Purpose |
|----------|------|------------|---------|
| `rsa2048_test.pem` / `rsa2048_test_pub.pem` | RSA | 2048-bit | Fast testing, development |
| `rsa4096_test.pem` / `rsa4096_test_pub.pem` | RSA | 4096-bit | Production-like testing, certificate generation |
| `ec256_test.pem` / `ec256_test_pub.pem` | ECDSA | P-256 (secp256r1) | ECC testing, JWT signing |

## Usage

### TI FEK Public Key (for certificate generation)
Use `rsa4096_test_pub.pem` as the TI FEK public key when generating OTP certificates:
```bash
cst --device f29h85x gencert -t test_keys/rsa4096_test_pub.pem --msv 0x1E22D ...
```

### Development Session Keys
Use the private keys for creating development sessions:
```bash
cst genkeys -s test_dev -p test123 --key-type rsa
```

### Note
These are **test keys only**. Do not use in production. The private keys are unencrypted for convenience in testing.