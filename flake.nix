{
  description = "Chrysalis Pi package, optional NixOS integration and persistent installer";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pi.url = "github:earendil-works/pi/v1.2.0";
    pi.inputs.nixpkgs.follows = "nixpkgs";
    disko.url = "github:nix-community/disko";
    disko.inputs.nixpkgs.follows = "nixpkgs";
    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-parts.inputs.nixpkgs-lib.follows = "nixpkgs";
    import-tree.url = "github:vic/import-tree";
    home-manager.url = "github:nix-community/home-manager";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
    nix-agent.url = "github:JEFF7712/nix-agent/dc12e28b1917d677bf5bf9f6ea607001b0591e1c";
    nix-agent.inputs.nixpkgs.follows = "nixpkgs";
  };
  outputs =
    inputs@{ self, nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      each = nixpkgs.lib.genAttrs systems;
    in
    {
      packages =
        each (
          system:
          let
            pkgs = import nixpkgs { inherit system; };
          in
          {
            default = pkgs.callPackage ./nix/package.nix { };
            chrysalis = self.packages.${system}.default;
          }
        )
        // {
          x86_64-linux = {
            default = (import nixpkgs { system = "x86_64-linux"; }).callPackage ./nix/package.nix { };
            chrysalis = self.packages.x86_64-linux.default;
            installer = self.nixosConfigurations.installer.config.system.build.image;
          };
        };
      nixosModules.default = import ./nix/modules/default.nix { inherit inputs self; };
      nixosModules.installer = import ./nix/modules/installer.nix { inherit inputs self; };
      homeManagerModules.default = import ./nix/modules/home.nix { inherit inputs self; };
      nixosConfigurations.installer = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          self.nixosModules.installer
          (nixpkgs + "/nixos/modules/virtualisation/disk-image.nix")
          {
            image.format = "raw";
            image.baseName = "chrysalis-installer-x86_64";
          }
        ];
      };
      checks =
        nixpkgs.lib.recursiveUpdate
          (each (
            system:
            let
              pkgs = import nixpkgs { inherit system; };
              moduleSystem = nixpkgs.lib.nixosSystem {
                inherit system;
                modules = [
                  self.nixosModules.default
                  {
                    nixpkgs.hostPlatform = system;
                    networking.hostName = "module-contract";
                    system.stateVersion = "26.05";
                    users.users.chrysalis.isNormalUser = true;
                    programs.chrysalis-pi = {
                      enable = true;
                      user = "chrysalis";
                      terminal.enable = false;
                    };
                  }
                ];
              };
            in
            {
              package = self.packages.${system}.default;
              module = pkgs.runCommand "chrysalis-module-contract" {
                contract = builtins.toJSON {
                  architecture = moduleSystem.config.nixpkgs.hostPlatform.system;
                  mode = moduleSystem.config.programs.chrysalis-pi.mode;
                  user = moduleSystem.config.programs.chrysalis-pi.user;
                  persistent = moduleSystem.config.programs.chrysalis-pi.stateDirectory;
                  runtime = moduleSystem.config.environment.variables.CHRYSALIS_EXECUTION_CONFIG;
                };
              } ''printf '%s\n' "$contract" > "$out"'';
            }
          ))
          {
            x86_64-linux.system = import ./nix/tests/system.nix {
              inherit self;
              pkgs = import nixpkgs { system = "x86_64-linux"; };
            };
          };
      formatter = each (system: nixpkgs.legacyPackages.${system}.nixfmt);
    };
}
