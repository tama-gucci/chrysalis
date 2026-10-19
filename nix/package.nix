{
  lib,
  buildNpmPackage,
  importNpmLock,
  nodejs_24,
  makeWrapper,
}:
buildNpmPackage {
  pname = "chrysalis";
  version = (builtins.fromJSON (builtins.readFile ../package.json)).version;
  src = lib.cleanSourceWith {
    src = ../.;
    filter =
      p: type:
      !(builtins.elem (baseNameOf p) [
        ".git"
        "node_modules"
        "result"
      ]);
  };
  nodejs = nodejs_24;
  npmDeps = importNpmLock { npmRoot = ../.; };
  npmConfigHook = importNpmLock.npmConfigHook;
  npmFlags = [
    "--ignore-scripts"
    "--legacy-peer-deps"
  ];
  dontNpmBuild = true;
  nativeBuildInputs = [ makeWrapper ];
  postInstall = ''
    makeWrapper ${nodejs_24}/bin/node "$out/bin/chrysalis-system-helper" \
      --add-flags "--import $out/lib/node_modules/chrysalis/node_modules/tsx/dist/loader.mjs" \
      --add-flags "$out/lib/node_modules/chrysalis/src/system/cli.ts"
  '';
  meta = {
    description = "Portable Pi package and optional NixOS onboarding";
    license = lib.licenses.mit;
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
  };
}
