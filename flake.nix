{
  description = "Guitar practice system development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      python = pkgs.python312.withPackages (ps: [
        ps.pip
        ps.setuptools
        ps.ruff
      ]);
      soundfont = "${pkgs.soundfont-fluid}/share/soundfonts/FluidR3_GM2-2.sf2";
      guitarctl = pkgs.writeShellApplication {
        name = "guitarctl";
        runtimeInputs = [ python ];
        text = ''
          exec python -m guitar_practice.interfaces.cli.main "$@"
        '';
      };
      toolchain = with pkgs; [
        python
        guitarctl
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

      # Run the same package-native trust gate in a pinned Nix environment.
      # Copy the flake source into writable storage: compileall and unittest
      # need to create temporary files without modifying the Nix store.
      checks.${system} = {
        repository-validation = pkgs.runCommand
        "guitar-practice-repository-validation"
        { nativeBuildInputs = [ python guitarctl ]; }
        ''
          cp -R ${self} source
          chmod -R u+w source
          cd source
          export HOME="$TMPDIR"
          export PYTHONPATH="$PWD"
          export GUITAR_SOUNDFONT="${soundfont}"
          guitarctl validate repo > "$TMPDIR/repository-validation.json"
          mkdir -p "$out"
          cp "$TMPDIR/repository-validation.json" "$out/report.json"
        '';

        toolchain = pkgs.runCommand "guitar-practice-toolchain-check" {
        nativeBuildInputs = toolchain;
      } ''
        command -v python >/dev/null
        command -v guitarctl >/dev/null
        command -v ruff >/dev/null
        command -v mscore >/dev/null
        command -v fluidsynth >/dev/null
        command -v ffmpeg >/dev/null
        test -f ${soundfont}
        touch $out
      '';
      };
    };
}
