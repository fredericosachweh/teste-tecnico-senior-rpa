{
  description = "Teste Técnico - Desenvolvedor Senior RPA BP";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        python = pkgs.python313;

        pythonEnv = python.withPackages (ps: with ps; [
          pip
          setuptools
          wheel
          ruff
          black
          pytest
          pytest-cov
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv
            uv

          #   chromium
            chromedriver
          ];

          shellHook = ''
            export UV_LINK_MODE=copy

            export CHROMEDRIVER_PATH=${pkgs.chromedriver}/bin/chromedriver
          '';

          LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
            pkgs.stdenv.cc.cc
            pkgs.zlib
            pkgs.glib
            pkgs.nspr
            pkgs.nss
          #   pkgs.dbus
          #   pkgs.atk
          #   pkgs.at-spi2-atk
          #   pkgs.cups
          #   pkgs.expat
          #   pkgs.libxcb
          #   pkgs.libxkbcommon
          #   pkgs.at-spi2-core
          #   pkgs.libX11
          #   pkgs.libXcomposite
          #   pkgs.libXdamage
          #   pkgs.libXext
          #   pkgs.libXfixes
          #   pkgs.libXrandr
          #   pkgs.mesa
          #   pkgs.libgbm
          #   pkgs.cairo
          #   pkgs.pango
          #   pkgs.systemd
          #    pkgs.alsa-lib
          ];

          PYTHONPATH = "${toString ./.}";
        };
      }
    );
}
