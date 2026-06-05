# cst CLI Commands Documentation

This document provides a comprehensive reference for the CyberShield Toolkit (cst) CLI commands for the F29H85x device family.

## Table of Contents

1. [SoC ID Operations](#soc-id-operations)
2. [Key Generation](#key-generation)
3. [Certificate Generation](#certificate-generation)
4. [Device Type Detection](#device-type-detection)
5. [UART Provisioning](#uart-provisioning)
6. [Device Recovery](#device-recovery)
7. [Root of Trust Certificate](#root-of-trust-certificate)
8. [Debug Certificate](#debug-certificate)
9. [Application Signing](#application-signing)
10. [JTAG Provisioning](#jtag-provisioning)

---

## SoC ID Operations

### Parse SoC ID
Parse and analyze System-on-Chip identification data.

```bash
cst --device f29h85x parseSoCId -s <soc_id_string>
```

**Example:**
```bash
cst --device f29h85x parseSoCId -s 0617ff0000000000000001004632394838355800000000000a00cdab0000010001000000020000000100000000000000000000000000000000000000ea0a5e7e2acbf7b587821766454242f87a23ca45cc1ad0d595661468eb571558b019a4cd88ac5c2e901ce8ca171c2dceed66273e8796c839597402eff5c32ccfce0c44734447afec12ba0b2226c3bdbc15576d212323ece46a9c4ccd6a463e417086083fee572a09a9496dbed447a9f13f9cf535fad75b18e0ee095a4e783c62f428831c8cf37ad269b3c162470e649f2f41876581744f517ad263936d6e22beb4eeb8383155f3142250b1bf27a6d8cc5bbda14c
```

### Get SoC ID via UART
Retrieve SoC ID from device connected via UART.

```bash
cst --device f29h85x getSoCId --port <port> --timeout <seconds>
```

**Example:**
```bash
cst --device f29h85x getSoCId --port /dev/ttyACM0 --timeout 10
```

---

## Key Generation

### Generate Keys
Generate cryptographic keys for device provisioning.

```bash
cst --device f29h85x --smpk_signing_algorithm <algorithm> --bmpk_signing_algorithm <algorithm> genkeys -s <session_name> -p <password>
```

**Example:**
```bash
cst --device f29h85x --smpk_signing_algorithm secp256r1 --bmpk_signing_algorithm secp384r1 genkeys -s rsa_f29_new -p 123#
```

**Parameters:**
- `--smpk_signing_algorithm`: Signing algorithm for SMPK (e.g., secp256r1, rsa4k)
- `--bmpk_signing_algorithm`: Signing algorithm for BMPK (e.g., secp384r1, rsa4k)
- `-s`: Session name
- `-p`: Password for key protection

---

## Certificate Generation

### Generate OTP Certificate
Generate One-Time Programmable (OTP) certificates for device provisioning.

```bash
cst --device f29h85x --smpk_signing_algorithm <algorithm> gencert -t <tifek_path> --msv <value> [options]
```

**Basic Example:**
```bash
cst --device f29h85x --smpk_signing_algorithm secp256r1 gencert -t /home/mitul/tisecprov/host/src/apps/tifs/otp_cert_gen/tifek/f29h85x/SR_10/ti_fek_public.pem --msv 0x1E22D --msv_protect --bmpk --bmek --b_protect --bmek_protect --smpk --smek --s_protect --smek_protect --sr_sbl 1 --sr_hsmRT 1 --sr_app 1 --sr_ssu 1 --keycnt 2 --keycnt_protect --keyrev 1 -d f29h85x --devSrVer SR_10 --ext_otp 0x80000001 --ext_otp_indx 0 --ext_otp_size 32
```

**With Session:**
```bash
cst --device f29h85x --session <session_name> --password <password> gencert -t <tifek_path> [options]
```

**Key Parameters:**
- `-t`: Path to TI FEK (Field Encryption Key) public key
- `--msv`: Minimum Software Version
- `--msv_protect`: Enable MSV protection
- `--bmpk`: Include Boot Mode Public Key
- `--bmek`: Include Boot Mode Encryption Key
- `--smpk`: Include Secure Mode Public Key
- `--smek`: Include Secure Mode Encryption Key
- `--keycnt`: Key count
- `--keyrev`: Key revision
- `--devSrVer`: Device silicon revision
- `--ext_otp`: Extended OTP value
- `--ext_otp_indx`: Extended OTP index
- `--ext_otp_size`: Extended OTP size

---

## Device Type Detection

### JTAG Device Type Detection
Detect device type and capabilities via JTAG interface.

```bash
spt --device f29h85x devTypeJTAG --ccs-path <ccs_path> --verbose
```

**Example:**
```bash
spt --device f29h85x devTypeJTAG --ccs-path ~/ti/ccs2030/ --verbose
```

### UART Device Type Detection
Detect device type via UART interface.

```bash
cst --device f29h85x devTypeUART --uart-kernel <kernel_path> --port <port> --targetbaud <baudrate>
```

**Example:**
```bash
cst --device f29h85x devTypeUART --uart-kernel /home/mitul/workspace_ccstheia/ram_based_uart_sbl/SECURE_KP_AND_CP/ram_based_uart_sbl.bin --port /dev/ttyACM0 --targetbaud 921600
```

---

## UART Provisioning

### UART Key Provisioning
Provision cryptographic keys via UART interface.

```bash
cst --device f29h85x uart_keyprov --otp-kw-bin <otp_keywriter_bin> --uart-kernel <uart_kernel> --certificate <cert_path> --port <port>
```

**Example:**
```bash
cst --device f29h85x uart_keyprov --otp-kw-bin ~/tisecprov/host/bin/asm/f29h85x/otp_kw_f29h85x_hs_fs.hsmimage.bin --uart-kernel ~/tisecprov/host/bin/asm/f29h85x/ex3_uart_flash_kernel_kp.cert.bin --certificate ~/ti/f29h85x/certificates/final_certificate.bin --port /dev/ttyACM0
```

### UART Code Provisioning
Provision firmware code via UART interface.

```bash
cst --device f29h85x uart_codeprov --uart-kernel <uart_kernel> --hsm-image <hsm_image> --hsm-cpu-code <hsm_cpu_code> --c29-cpu-code <c29_code> --seccfg <seccfg_path> --port <port> --targetbaud <baudrate> --input <input_sequence>
```

**Example:**
```bash
cst --device f29h85x uart_codeprov --uart-kernel ~/tisecprov/host/bin/asm/f29h85x/ram_based_uart_sbl_secure_kp_cp.bin --hsm-image /home/mitul/tifs/hsm_firmware/f29h85x/code_provisioning/hsm0-0_nortos/ti-arm-clang/tifs_f29h85x_hs_se_code_provisioning.release.hs.hsmimage --hsm-cpu-code ~/ti/f29h85x/signedImages/tifs_f29h85x_hs_se.release.hs.hsmimage --c29-cpu-code ~/ti/f29h85x/signedImages/main.cert.bin --seccfg /home/mitul/main.bin --port /dev/ttyACM0 --targetbaud 921600 --input 3,5,6,7
```

---

## Device Recovery

### Enable Device Recovery
Enable device recovery mode.

```bash
cst --device f29h85x endevrecov --ccs-path <ccs_path> --verbose
```

**Example:**
```bash
cst --device f29h85x endevrecov --ccs-path ~/ti/ccs2030/ --verbose
```

### Get UID and Security Capabilities
Retrieve device UID and security capabilities.

```bash
cst --device f29h85x getUIDSecap --ccs-path <ccs_path> --verbose
```

**Example:**
```bash
cst --device f29h85x getUIDSecap --ccs-path ~/ti/ccs2030/ --verbose
```

### Generate Device Recovery Certificate
Generate device recovery certificate using device UID.

```bash
cst --device f29h85x --smpk_signing_algorithm <algorithm> --bmpk_signing_algorithm <algorithm> devicerecovery --keyrev <revision> --dev_uid <device_uid>
```

**Examples:**
```bash
# Using direct signing algorithms
cst --device f29h85x --smpk_signing_algorithm rsa4k --bmpk_signing_algorithm rsa4k devicerecovery --keyrev 1 --dev_uid AF33F0E1BA285E3C79141B4976E88587AD8D2ACCFD7A3E7A4CF50C96E431CB03B32998A10CF3E84B21AE51EEE118D2A2074B36FD53B13BAF11FBA168C9833FB3

# Using session
cst --device f29h85x --session rsa_f29_new --password 123# devicerecovery --keyrev 1 --dev_uid AF33F0E1BA285E3C79141B4976E88587AD8D2ACCFD7A3E7A4CF50C96E431CB03B32998A10CF3E84B21AE51EEE118D2A2074B36FD53B13BAF11FBA168C9833FB3
```

### Validate Device Recovery Certificate
Validate a device recovery certificate.

```bash
cst --device f29h85x valdcert --dev_recov_cert <cert_path> --ccs-path <ccs_path> --verbose
```

**Example:**
```bash
cst --device f29h85x valdcert --dev_recov_cert /home/mitul/ti/f29h85x/device_recovery/device_recovery.bin --ccs-path ~/ti/ccs2030/ --verbose
```

---

## Root of Trust Certificate

### Generate Root of Trust Certificate
Generate Root of Trust (RoT) certificate.

```bash
cst --device f29h85x --smpk_signing_algorithm <algorithm> --bmpk_signing_algorithm <algorithm> rotcert
```

**Examples:**
```bash
# Using direct signing algorithms
cst --device f29h85x --smpk_signing_algorithm rsa4k --bmpk_signing_algorithm rsa4k rotcert

# Using session
cst --device f29h85x --session rsa_f29_new --password 123# rotcert
```

---

## Debug Certificate

### Generate Debug Certificate
Generate debug certificate for development and debugging purposes.

```bash
cst --device f29h85x --smpk_signing_algorithm <algorithm> --bmpk_signing_algorithm <algorithm> debugcert --keyrev <revision> --swrv <sw_revision> --dev_dbg_type <debug_type> --dev_uid <device_uid>
```

**Examples:**
```bash
# Using direct signing algorithms
cst --device f29h85x --smpk_signing_algorithm rsa4k --bmpk_signing_algorithm rsa4k debugcert --keyrev 1 --swrv 1 --dev_dbg_type 4 --dev_uid 2B30EFDBE1D6A92F57318AC0AF2FE89AC3B2950C6418C587DCD30E93A168C9BD300B1F558ADDD394D452E724EEA3977568984DC3DB97AAF9E3920D8C3C724C40

# Using session
cst --device f29h85x --session rsa_f29 --password 123# debugcert --keyrev 1 --swrv 1 --dev_dbg_type 4 --dev_uid 2B30EFDBE1D6A92F57318AC0AF2FE89AC3B2950C6418C587DCD30E93A168C9BD300B1F558ADDD394D452E724EEA3977568984DC3DB97AAF9E3920D8C3C724C40
```

**Parameters:**
- `--keyrev`: Key revision number
- `--swrv`: Software revision number
- `--dev_dbg_type`: Debug type (e.g., 4 for specific debug level)
- `--dev_uid`: Device unique identifier

---

## Application Signing

### Sign Application Images
Sign various application images for different cores and boot modes.

```bash
cst --device f29h85x --smpk_signing_algorithm <algorithm> --bmpk_signing_algorithm <algorithm> <signapp/signSecCfg> --image <image_path> --input-format <format> --core <core_type> --keyrev <revision> --loadaddr <address> --swrv <sw_revision> --boot <boot_mode> [--debug <debug_level>]
```

**Examples:**

#### Sign C29 Core Application (Flash Boot)
```bash
cst --device f29h85x --smpk_signing_algorithm rsa4k --bmpk_signing_algorithm rsa4k signapp --image ~/tisecprov/host/bin/asm/f29h85x/csd.bin --input-format BIN --core C29 --keyrev 1 --loadaddr 0x10001000 --swrv 1 --boot FLASH
```

#### Sign C29 Core Application (RAM Boot)
```bash
cst --device f29h85x --smpk_signing_algorithm rsa4k --bmpk_signing_algorithm rsa4k signapp --image ~/tisecprov/host/bin/asm/f29h85x/ram_based_uart_sbl_secure_kp_cp.bin --input-format BIN --core C29 --keyrev 1 --loadaddr 0x200E1000 --swrv 1 --boot RAM
```

#### Sign HSM Core Application (Flash Boot)
```bash
cst --device f29h85x --smpk_signing_algorithm rsa4k --bmpk_signing_algorithm rsa4k signapp --image ~/tisecprov/host/bin/asm/f29h85x/tifs_f29h85x_hs_se.release.bin --input-format BIN --core HSM --keyrev 1 --loadaddr 0x00000000 --swrv 1 --debug DBG_SOC_DEFAULT --boot FLASH
```

#### Sign HSM Core Application (RAM Boot)
```bash
cst --device f29h85x --smpk_signing_algorithm rsa4k --bmpk_signing_algorithm rsa4k signapp --image ~/tisecprov/host/bin/asm/f29h85x/tifs_f29h85x_hs_se_code_provisioning.release.bin --input-format BIN --core HSM --keyrev 1 --loadaddr 0x00000000 --swrv 1 --debug DBG_SOC_DEFAULT --boot RAM
```

#### Sign Security Configuration
```bash
cst --device f29h85x --smpk_signing_algorithm rsa4k --bmpk_signing_algorithm rsa4k signSecCfg --swrv 1 --keyrev 1 --ccs-path ~/ti/ccs2030 --image /home/mitul/ti/c29_sdk/mcu_sdk_f29h85x/source/defseccfgbin/default_seccfg_bankmode_0_ssumode1.out --output_path ~/ti/f29h85x/signedImages --boot FLASH
```

**Parameters:**
- `--image`: Path to the image file to sign
- `--input-format`: Input file format (BIN, OUT, etc.)
- `--core`: Target core (C29, HSM)
- `--keyrev`: Key revision number
- `--loadaddr`: Load address in memory (hexadecimal)
- `--swrv`: Software revision number
- `--boot`: Boot mode (FLASH, RAM)
- `--debug`: Debug level (optional, e.g., DBG_SOC_DEFAULT)

---

## JTAG Provisioning

### JTAG Code Provisioning
Provision firmware code via JTAG interface.

```bash
cst --device f29h85x jtag_codeprov --ccs-path <ccs_path> --jtag-kernel <jtag_kernel> --hsm-image <hsm_image> --hsm-cpu-code <hsm_cpu_code> --c29-cpu-code <c29_code> --seccfg <seccfg_path> --verbose
```

**Example:**
```bash
cst --device f29h85x jtag_codeprov --ccs-path ~/ti/ccs2030/ --jtag-kernel /home/mitul/workspace_ccstheia/secure_ram_based_jtag_kernel/RAM/secure_ram_based_jtag_kernel.out --hsm-image /home/mitul/ti/f29h85x/signedImages/tifs_f29h85x_hs_se_code_provisioning.release.hs.hsmimage --hsm-cpu-code /home/mitul/ti/f29h85x/signedImages/tifs_f29h85x_hs_se.release.hs.hsmimage --c29-cpu-code /home/mitul/ti/f29h85x/signedImages/csd.cert.bin --seccfg /home/mitul/Downloads/seccfg_latest_rsa4k.bin --verbose
```

### JTAG Key Provisioning
Provision cryptographic keys via JTAG interface.

```bash
cst --device f29h85x jtag_keyprov --ccs-path <ccs_path> --otp-kw-bin <otp_keywriter_bin> --jtag-kernel <jtag_kernel> --certificate <cert_path>
```

**Example:**
```bash
cst --device f29h85x jtag_keyprov --ccs-path ~/ti/ccs2030/ --otp-kw-bin ~/tisecprov/host/bin/asm/f29h85x/otp_kw_f29h85x_hs_fs.hsmimage.bin --jtag-kernel ~/tisecprov/host/bin/asm/f29h85x/secure_ram_based_jtag_kernel.out --certificate ~/ti/f29h85x/certificates/final_certificate.bin
```

---

## Common Parameters

### Device Specification
- `--device f29h85x`: Specifies the target device family

### Signing Algorithms
- `--smpk_signing_algorithm`: Secure Mode Public Key signing algorithm
  - Options: `secp256r1`, `secp384r1`, `secp521r1`, `rsa4k`
- `--bmpk_signing_algorithm`: Boot Mode Public Key signing algorithm
  - Options: `secp256r1`, `secp384r1`, `secp521r1`, `rsa4k`

### Session Management
- `--session <name>`: Use existing key session
- `--password <password>`: Password for session access

### Common Paths
- `--ccs-path`: Path to Code Composer Studio installation
- `--port`: Serial port for UART communication (e.g., `/dev/ttyACM0`)
- `--targetbaud`: Target baud rate for UART communication

### Verbosity
- `--verbose`: Enable verbose output for debugging

---

## Notes

1. **File Paths**: All file paths in the examples are specific to the user's environment and should be adjusted accordingly.

2. **Device UID**: Device UIDs are unique 128-bit identifiers specific to each device and must be obtained from the actual hardware.

3. **Key Management**: When using sessions, ensure proper key management and password protection.

4. **Security**: These commands handle sensitive cryptographic operations. Ensure proper security practices when using in production environments.

5. **Prerequisites**: Ensure all required binaries, certificates, and configuration files are available before running provisioning commands.
