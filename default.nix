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
    uv = [ uv uvEnv ];
    scripts = pkgs.lib.attrsets.attrValues scripts;
  };

  scripts = with pkgs; { };
  paths = pkgs.lib.flatten [ (builtins.attrValues tools) ];
  env = pkgs.buildEnv {
    inherit name paths; buildInputs = paths;
  };
in
(env.overrideAttrs (_: {
  inherit name;
  NIXUP = "0.0.10";
} // uvEnv.uvEnvVars)) // { inherit scripts; }
