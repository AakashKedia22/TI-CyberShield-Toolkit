# TI CyberShield Toolkit — System Architecture

Interactive architecture map generated with [Archify](https://github.com/tt-a1i/archify) from the repository's runtime structure.

## Diagram

![TI CyberShield Toolkit runtime architecture](tisecprov.architecture.visual-check.1440x900.light.png)

## Interactive artifact

The self-contained interactive diagram is [`index.html`](./index.html).
Open it in any browser to focus nodes, trace upstream/downstream reach, probe exact routes,
compare semantic roles, switch light/dark themes, and play the three guided views. The typed
source specification is [`tisecprov.architecture.json`](./tisecprov.architecture.json).

To render the interactive HTML on GitHub, enable **GitHub Pages** for this repository
(Settings -> Pages, deploy from branch `http-api`, folder `/root`), then open:

```
https://<owner>.github.io/TI-CyberShield-Toolkit/archify/index.html
```

## Guided views

- **Keys to silicon** — generate sessions and signed images, then provision them to the target.
- **Key material stays local** — private keys and password-protected sessions never leave the crypto service.
- **Hardware jobs** — async, cancellable provisioning jobs over UART and JTAG/CCS.