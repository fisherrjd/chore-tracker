{ pkgs ? import
    (fetchTarball {
      name = "jpetrucciani-2026-06-04";
      url = "https://github.com/jpetrucciani/nix/archive/e5adfb44f73ac8a1e053c34330f642749f577e51.tar.gz";
      sha256 = "03qylaa6sw1wn762g0w5zcfy27584hpdk1fc91yisrbm2vcif79v";
    })
    { }
}:
let
  name = "chore-tracker";
  uvEnv = pkgs.uv-nix.mkEnv {
    inherit name; python = pkgs.python314;
    workspaceRoot = pkgs.hax.filterSrc { path = ./.; };
    pyprojectOverrides = final: prev: { };
  };

  tools = with pkgs; {
    cli = [
      jfmt
      nixup
    ];
    bun = [ bun ];
    uv = [ uv uvEnv ];
    scripts = pkgs.lib.attrsets.attrValues scripts;
  };

  scripts = with pkgs; {
    ui-update = pog {
      name = "ui-update";
      description = "pull the latest shared styles/components (@fisherrjd/ui) and typecheck";
      script = ''
        cd "$(git rev-parse --show-toplevel)/frontend" || exit 1
        # bun.lock pins the ui commit as github:fisherrjd/ui#<sha>
        rev() { grep -oE 'github:fisherrjd/ui#[0-9a-f]+' bun.lock | head -1 | cut -d'#' -f2; }
        before=$(rev)
        bun update @fisherrjd/ui
        after=$(rev)
        if [ "$before" = "$after" ]; then
          echo "✓ already on the latest @fisherrjd/ui ($after)"
          exit 0
        fi
        echo "→ @fisherrjd/ui $before → $after"
        echo "  https://github.com/fisherrjd/ui/compare/$before...$after"
        bun run typecheck
        echo ""
        echo "✅ updated — eyeball /styleguide (dev), then commit frontend/bun.lock"
      '';
    };
  };
  paths = pkgs.lib.flatten [ (builtins.attrValues tools) ];
  env = pkgs.buildEnv {
    inherit name paths; buildInputs = paths;
  };
in
(env.overrideAttrs (_: {
  inherit name;
  NIXUP = "0.0.10";
} // uvEnv.uvEnvVars)) // { inherit scripts; }
