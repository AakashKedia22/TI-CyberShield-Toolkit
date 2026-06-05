# Introduction

This repository has the Python SDK and the GUI for the secure provisioning
of TI EP SoCs.

# Installation

At the moment, we need a working installation of Python 3.10 or above
on the host computer where you want to run the tool. In future, we
would be providing installers for the tool which does not assume an
installed version of Python on the host computer. It is also assumed
that the host computer has the Python package installer `pip`
installed.

Execute these commands at the root of the source code in the file
system.

## Install virtualenv either from your OS package manager or via pip

```
cd host
pip install virtualenv
```

## Create a virtual environment

```
virtualenv venv
source venv/bin/activate
```

## install the package and dependencies into the virtualenv

```
pip install -e.
```

If you want to develop the code, run tests etc, modify the above command to
```
pip install -e.[dev]
```

The valid optional dependency groups are "dev", "gui" and "docs".

Once this is done, you will have access to `cst` command.

### GUI

To install the dependencies for GUI, do
```
pip install -e.[gui]
```

The GUI program is `qtgui` (for now!).

## Alternate installation with Nix

If you are a nix user, you can install with [nix package manager](https://nix.dev/manual/nix/2.28/).

From the `host` directory:
```
nix-build
```
This should create `cst` and `cstgui` in `results/bin` directory.

The following command should give you access to the commands in your environment.

```
nix-env -i ./result
```

# Usage

The "applications" are in the apps directory. The CLI app is called
`cst`, which has a number of sub-commands.

```
$ cst
usage: cst [-h] {genkeys,gencert,sign,encrypt,download} ...

TI Cybershield Toolkit

options:
  -h, --help            show this help message and exit

commands:
  valid commands

  {genkeys,gencert,sign,encrypt,download}
    genkeys             Generate Manufacturer keys
    gencert             Generate an x.509 certificate
    sign                Sign a binary with the given private key
    encrypt             encrypt a binary with the given symmetric key
    download            download a binary into the target
```

1. Step 1: Generate keys and store it in a "session". A session is a
password protected entity where the keys are stored and can be
retrieved later. Note the name of the session, as you will be
referring to this name for generating certificates.

```
$ cst genkeys -s "Session1" -p "test123" --key-type rsa
```

Options:

-s, --session: Name for the generated keys (required)
-p, --password: Password used to protect the keys on the disk (required)
--key-type: Key type to generate (default: rsa, choices: rsa, ecc)
--devel: Use development keys instead of generating new keys

2. Step 2: Generate the certificate.

```
$ cst gencert -s Session1 -p test123 --tifek-pub tifek/tifekpub.pem -o keycert.h
```

Here are the full options for the `gencert` sub-command:
```
cst gencert [-h] -s SESSION \
                 -p PASSWORD \
                 --tifek-pub TIFEK_PUB \
                 [--msv MSV] \
                 [--mpk-options MPK_OPTIONS] \
                 [--mek-options MEK_OPTIONS] \
                 [--signing-algorithm {rsa-pss,rsa-pkcs1v1.5}] \
                 [-multishot MULTI_SHOT] \
                 -o OUTPUT
```
If you don't specify msv, mpk-options etc, certain defaults are used. The MPK_OPTIONS
and the MEK_OPTIONS are specified as comma separated string, for example:

```
--mpk-options "wp, ovrd"
```

or

```
--mek-options "wp"
```

3. Step 3: Build the key writer binary with the generated `keycert.h`

4. Step 4: Download the binary into the target via serial port

The user should have permissions to read/write into the serial
port. To do that add the username into the group called `plugdev` and
`dialout`.

```
sudo adduser <username> dialout
sudo adduser <username> plugdev
```

DO NOT run `cst` or `cstgui` as root or under `sudo`. There is no need
for it. Instead fix the permissions by adding the user to the right
group.

First note down the serial port that is connected to the target. To
download the built keywriter target executable into the target:

```
cst download -p <serial port> -b <keywriter-binary>
```

5. Step 5. Open the serial port to inspect the logs

Once the keywriter binary is downloaded into the target, open a
program like `minicom` on GNU/Linux with the same port and baudrate to
look at the OTP key writing process logs.

If the key writing process is successful, after reboot, the SoC ID can
be inspected to see if the SoC got converted from HS-FS to HS-SE.

# Device Addons: Secure Binaries and TI FEK Keys

Device-specific secure binaries and TI FEK public keys live in `host/addons/<device>/`
inside the repository (git-tracked for developer access, excluded from the PyInstaller
build). They are distributed out-of-band as zip archives and installed separately for
runtime use.

## Repo layout (`host/addons/`)

```
host/addons/
    f29h85x/
        bin/
            otp_kw_f29h85x_hs_fs.hsmimage.bin
            otp_kw_f29h85x_hs_se.hsmimage.bin
            tifs_f29h85x_hs_se.release.bin
            tifs_f29h85x_hs_se_code_provisioning.release.bin
            combined_services_demo.bin
            secure_boot_manager.bin
            default_seccfg_bankmode_0_ssumode1.out
        tifek/
            SR_10/
                ti_fek_public.pem
    am261x/
        tifek/SR_10/ti_fek_public.pem
    am263x/
        tifek/SR_11/ti_fek_public.pem
    am263px/
        tifek/SR_10/ti_fek_public.pem
    am273x/
        tifek/SR_10/ti_fek_public.pem
        tifek/SR_11_12/ti_fek_public.pem
```

> **Note:** `ram_based_uart_sbl.bin`, `secure_ram_based_jtag_kernel.out`, and
> `uart_flash_programmer` are not secure assets and are shipped directly in
> `host/bin/asm/f29h85x/`.

## Creating an addon zip (internal/release use)

Run from the `host/` directory:

```
python pack_addon.py --device <device> [--version <ver>] [--out <dir>]
```

The script packs from `host/addons/<device>/` in the repo. Examples:

```
python pack_addon.py --device f29h85x
# → host/f29h85x_addon.zip

python pack_addon.py --device am263x
# → host/am263x_addon.zip

python pack_addon.py --device f29h85x --version 1.0.0 --out /tmp
# → /tmp/f29h85x_addon_1.0.0.zip
```

The script verifies all expected files are present before creating the zip, and prints
the output path, file count, and size on success. Supported devices: `f29h85x`,
`am261x`, `am263x`, `am263px`, `am273x`.

To add support for a new device, add an entry to `DEVICE_CONFIGS` in `pack_addon.py`.

# Using cst with pkcs#11 HSM smartcards

The tool is tested with Nitrokey HSM2 with the sc-hsm-pkcs11 driver
module. By default, we look for module installation in
`/usr/local/lib`. However, if the user has installed it in another
directory, it can be specified with the environment variable
`PKCS11_LIB`. Note that this has only been tested on GNU/Linux.

It is expected that the user has initialized the card and given it a
name/pin/so-pin externally using the `sc-hsm-tool`. For example:

```
$ sc-hsm-tool --initialize --so-pin 3132333435363738 --pin 123456 --label HSM
```

# Hacking

Please see the [Design
Document](https://confluence.itg.ti.com/display/K3ROM/Design) and the
[GUI Design
Considerations](https://confluence.itg.ti.com/display/K3ROM/Secure+Provisioning+Tool+-+GUI+design+considerations)
page. There are other documents like weekly meeting notes etc in the
[Secure Provisioning
Homepage](https://confluence.itg.ti.com/display/K3ROM/Secure+Provisioning+Homepage).

The program is structured as a `tisecprov` package and applications (a
cli application called `cst` (Cybershield Toolkit) and `cstgui`, a GUI version of the
program), for the tool Cybershield Toolkit. The `tisecprov` follows the
[src](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
based packaging scheme.

Here are a few guidelines for developers working on this codebase.

1. Use `mypy` and `typing` module as much as possible to use and
   verify [PEP 484](https://peps.python.org/pep-0484/) type hints.
2. Write small, testable functions. If a function need access to files
   to read or write, then write the logic of it that takes the file
   content as a separate function and use it inside the one that uses
   files, so that the inner function can be tested.
3. Write as many tests as possible so that we can run it on CI and
   measure code coverage and have more confidence on the code.
4. Do not "shell out" and call other executable. Instead use a library
   that wraps the API. (eg: python `cryptography` library instead of
   shelling out to `openssl`).
5. Add docstrings to every function and class that you are adding.
6. Unless the CI is green, do not push new changes.
7. We use `black` for code formatting. Please run `make format` before
   submitting a pull request.
8. Linting is done with `pylint`. Please run `make lint` before
   submitting a pull request.
9. Think twice before adding a new dependency. Can it be solved with a
   standard library function or a self written function? If you use
   only a function from a library, does it make sense to just copy
   that function alone into a module and use it? If so, pay attention
   to the license and give due credit to the authors and respect their
   license terms.

## Submitting PRs.

1. Create a branch that looks roughly like this:
```
<your AID>_some_descriptive_name_for_pr
```
2. Make self contained commits that touches only one thing that you
   like to change. If there are multiple things you want to change,
   make separate PRs.
3. Multiple commits in one PR is perfectly fine. You need not squash
   them into one PR.
4. Follow the instructions in the PR template.
5. Once your PR is approved, respnsibility of merging the PR is with
   the author of the PR.
6. Do not commit anything directly into `master`. Instead, always
   create feature branches named with the above convensions and get
   the changes reviewed before merging it.

