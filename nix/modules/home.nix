{ inputs, self }:
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.chrysalis-pi;
  system = pkgs.stdenv.hostPlatform.system;
  package = cfg.package;
  piWithChrysalis = pkgs.symlinkJoin {
    name = "pi-with-chrysalis";
    paths = [ cfg.piPackage ];
    nativeBuildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      wrapProgram $out/bin/pi --add-flags "--extension ${package}/lib/node_modules/chrysalis"
    '';
  };
in
{
  options.programs.chrysalis-pi = {
    enable = lib.mkEnableOption "the ordinary Chrysalis Pi package";
    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${system}.default;
    };
    piPackage = lib.mkOption {
      type = lib.types.package;
      default = inputs.pi.packages.${system}.default;
    };
  };
  config = lib.mkIf cfg.enable {
    programs.pi-coding-agent = {
      enable = true;
      package = lib.mkDefault piWithChrysalis;
      extraPackages = [
        package
        pkgs.nodejs_24
        pkgs.git
      ];
    };
  };
}
