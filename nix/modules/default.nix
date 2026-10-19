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
  tmpfilesPath =
    value: lib.replaceStrings [ "\\" " " "%" "'" "\"" ] [ "\\x5c" "\\x20" "%%" "\\x27" "\\x22" ] value;
  packageRoot = "${cfg.package}/lib/node_modules/chrysalis";
  agent =
    if cfg.mode == "installer" then
      "${inputs.nix-agent.packages.${system}.default}/bin/nix-agent"
    else
      "/run/current-system/sw/bin/nix-agent";
  native = pkgs.writeText "chrysalis-system.json" (
    builtins.toJSON {
      version = 1;
      inherit (cfg) mode host;
      timeZone = if config.time.timeZone == null then "Etc/UTC" else config.time.timeZone;
      configuration = cfg.configurationDirectory;
      state = cfg.stateDirectory;
      source = "${self}";
      commands = {
        nix = "${pkgs.nix}/bin/nix";
        sudo = "/run/wrappers/bin/sudo";
        disko = "${inputs.disko.packages.${system}.disko-install}/bin/disko-install";
        lsblk = "${pkgs.util-linux}/bin/lsblk";
        findmnt = "${pkgs.util-linux}/bin/findmnt";
        facter = "${pkgs.nixos-facter}/bin/nixos-facter";
        mkpasswd = "${pkgs.mkpasswd}/bin/mkpasswd";
        nixAgent = agent;
        node = "${pkgs.nodejs_24}/bin/node";
      };
    }
  );
  executionFHS =
    (pkgs.buildFHSEnv {
      name = "chrysalis-execution-runtime";
      targetPkgs = p: [
        p.bash
        p.coreutils
        p.nodejs_24
        p.util-linux
      ];
      multiPkgs = _: [ ];
      multiArch = false;
    }).fhsenv;
  executionClosure = pkgs.closureInfo {
    rootPaths = [
      executionFHS
      pkgs.nodejs_24
    ];
  };
  execution = pkgs.writeText "chrysalis-execution.json" (
    builtins.toJSON {
      version = 1;
      arch = if pkgs.stdenv.hostPlatform.isx86_64 then "x64" else "arm64";
      bwrap = "${pkgs.bubblewrap}/bin/bwrap";
      systemdRun = "${config.systemd.package}/bin/systemd-run";
      systemctl = "${config.systemd.package}/bin/systemctl";
      node = "${pkgs.nodejs_24}/bin/node";
      usr = "${executionFHS}/usr";
      storePaths = "${executionClosure}/store-paths";
    }
  );
  session = pkgs.writeShellScriptBin "chrysalis-session" ''
    set -eu
    export CHRYSALIS_SYSTEM_CONFIG=/etc/chrysalis/system.json
    export CHRYSALIS_EXECUTION_CONFIG=${execution}
    export CHRYSALIS_STATE_ROOT=${lib.escapeShellArg cfg.stateDirectory}
    if [ ${lib.escapeShellArg cfg.mode} = installer ]; then
      export PI_CODING_AGENT_DIR="''${XDG_RUNTIME_DIR:?}/chrysalis-pi"
    else
      export PI_CODING_AGENT_DIR="$HOME/.pi/agent"
    fi
    mkdir -p "$PI_CODING_AGENT_DIR" "$CHRYSALIS_STATE_ROOT/pi-sessions"
    chmod 700 "$PI_CODING_AGENT_DIR" "$CHRYSALIS_STATE_ROOT/pi-sessions"
    if ! ${pkgs.networkmanager}/bin/nm-online -q -t 5; then
      ${pkgs.networkmanager}/bin/nmtui connect
    fi
    cd ${lib.escapeShellArg cfg.configurationDirectory}
    exec ${cfg.piPackage}/bin/pi --extension ${packageRoot} \
      --session-dir "$CHRYSALIS_STATE_ROOT/pi-sessions" --continue
  '';
  terminal = pkgs.writeShellScriptBin "chrysalis-terminal" ''
    exec ${pkgs.ghostty}/bin/ghostty --gtk-single-instance=false --window-decoration=false \
      -e ${pkgs.tmux}/bin/tmux -f /etc/chrysalis/tmux.conf new-session -A -s chrysalis ${session}/bin/chrysalis-session
  '';
in
{
  imports = [
    inputs.nix-agent.nixosModules.default
    inputs.home-manager.nixosModules.home-manager
  ];
  options.programs.chrysalis-pi = {
    enable = lib.mkEnableOption "the terminal-first Chrysalis system";
    user = lib.mkOption {
      type = lib.types.str;
      default = "chrysalis";
      description = "Existing normal user for the graphical Pi session";
    };
    host = lib.mkOption {
      type = lib.types.str;
      default = config.networking.hostName;
    };
    mode = lib.mkOption {
      type = lib.types.enum [
        "installer"
        "installed"
      ];
      default = "installed";
    };
    configurationDirectory = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/chrysalis/configuration";
    };
    stateDirectory = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/chrysalis/state";
    };
    terminal.enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
    };
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
    assertions = [
      {
        assertion = builtins.match "[a-zA-Z0-9_-]{1,63}" cfg.host != null;
        message = "Chrysalis requires one explicit host attribute.";
      }
      {
        assertion = cfg.user != "root" && config.users.users.${cfg.user}.isNormalUser;
        message = "Chrysalis must run as a normal configured user.";
      }
      {
        assertion =
          lib.hasPrefix "/" cfg.configurationDirectory
          && lib.hasPrefix "/" cfg.stateDirectory
          && cfg.configurationDirectory != cfg.stateDirectory
          &&
            lib.all (value: lib.all (c: builtins.match "[[:cntrl:]]" c == null) (lib.stringToCharacters value))
              [
                cfg.configurationDirectory
                cfg.stateDirectory
              ];
        message = "Chrysalis configuration and state require distinct absolute directories.";
      }
    ];
    nix.settings.experimental-features = [
      "nix-command"
      "flakes"
    ];
    environment.systemPackages = [
      cfg.package
      cfg.piPackage
      session
      terminal
      pkgs.tmux
      pkgs.bubblewrap
      pkgs.nodejs_24
      pkgs.git
      pkgs.nixos-facter
      pkgs.disko
      pkgs.networkmanager
      pkgs.mkpasswd
    ];
    environment.variables.CHRYSALIS_EXECUTION_CONFIG = "${execution}";
    environment.etc."chrysalis/execution.json".source = execution;
    environment.etc."chrysalis/system.json".source = native;
    environment.etc."chrysalis/package".source = packageRoot;
    environment.etc."chrysalis/package-source".source = self.outPath;
    environment.etc."chrysalis/tmux.conf".text = ''
      set -g default-terminal "tmux-256color"
      set -g allow-passthrough on
      set -g history-limit 20000
      set -g mouse on
    '';
    systemd.tmpfiles.rules = [
      "d ${tmpfilesPath cfg.configurationDirectory} 0700 ${tmpfilesPath cfg.user} users -"
      "d ${tmpfilesPath cfg.stateDirectory} 0700 ${tmpfilesPath cfg.user} users -"
    ]
    ++ lib.optionals (cfg.mode == "installer") [ "d /run/chrysalis 0700 ${cfg.user} users -" ];
    services.dbus.enable = true;
    networking.networkmanager.enable = true;
    programs.nix-agent = lib.mkIf (cfg.mode == "installed") {
      enable = true;
      flake = cfg.configurationDirectory;
      privilegedAutomation = {
        enable = true;
        user = cfg.user;
      };
    };
    home-manager = {
      useGlobalPkgs = lib.mkDefault true;
      useUserPackages = lib.mkDefault true;
      users.${cfg.user} = {
        imports = [ self.homeManagerModules.default ];
        programs.chrysalis-pi = {
          enable = true;
          package = cfg.package;
          piPackage = cfg.piPackage;
        };
        home.stateVersion = lib.mkDefault config.system.stateVersion;
        home.sessionVariables = {
          CHRYSALIS_SYSTEM_CONFIG = "/etc/chrysalis/system.json";
          CHRYSALIS_EXECUTION_CONFIG = "${execution}";
          CHRYSALIS_STATE_ROOT = cfg.stateDirectory;
        };
      };
    };
    services.cage = lib.mkIf cfg.terminal.enable {
      enable = true;
      user = cfg.user;
      program = "${terminal}/bin/chrysalis-terminal";
    };
    systemd.services.cage-tty1.serviceConfig = lib.mkIf cfg.terminal.enable {
      Restart = "always";
      RestartSec = 2;
    };
  };
}
