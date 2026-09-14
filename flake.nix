{
  description = "Guitar practice system development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      python = pkgs.python312.withPackages (ps: [
        ps.pip
        ps.setuptools
        ps.ruff
      ]);
      soundfont = "${pkgs.soundfont-fluid}/share/soundfonts/FluidR3_GM2-2.sf2";
      toolchain = with pkgs; [
        python
        musescore
        fluidsynth
        ffmpeg
        soundfont-fluid
      ];
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = toolchain;
        GUITAR_SOUNDFONT = soundfont;

        shellHook = ''
          export PYTHONPATH="$PWD''${PYTHONPATH:+:$PYTHONPATH}"
        '';
      };

      checks.${system}.toolchain = pkgs.runCommand "guitar-practice-toolchain-check" {
        nativeBuildInputs = toolchain;
      } ''
        command -v python >/dev/null
        command -v ruff >/dev/null
        command -v mscore >/dev/null
        command -v fluidsynth >/dev/null
        command -v ffmpeg >/dev/null
        test -f ${soundfont}
        touch $out
      '';
    };
}
