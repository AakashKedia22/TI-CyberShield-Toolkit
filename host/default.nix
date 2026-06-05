with import <nixpkgs> {};

python3Packages.buildPythonApplication rec {
  pname = "tisecprov";
  version = "0.1.0"; # From src/tisecprov/__init__.py

  src = ./.;

  format = "pyproject";

  propagatedBuildInputs = with python3Packages; [
    cryptography
    pyserial
    xmodem
    appdirs
    asn1crypto
    tqdm
    pyqt5
  ] ++ [
    # Add these Qt-related dependencies
    libsForQt5.qt5.qtbase
    xorg.libxcb
    libGL
  ];

  nativeBuildInputs = with python3Packages; [
    hatchling
    hatch-vcs
    qt5.wrapQtAppsHook

  ];

  buildInputs = with qt5; [
    qtbase
    qttools
  ];

  dontWrapGApps = true;
  preFixup = ''
    makeWrapperArgs+=("''${qtWrapperArgs[@]}")
  '';  # Added this block

  meta = with lib; {
    description = "TI  CyberShield Toolkit";
    license = licenses.mit;
  };
}

