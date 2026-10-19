{ inputs, self }:
{ lib, pkgs, ... }:
{
  imports = [ self.nixosModules.default ];
  networking.hostName = "chrysalis-installer";
  system.stateVersion = "26.05";
  users.users.chrysalis = {
    isNormalUser = true;
    extraGroups = [
      "wheel"
      "networkmanager"
      "video"
      "render"
    ];
    initialHashedPassword = "";
  };
  security.sudo.wheelNeedsPassword = false;
  programs.chrysalis-pi = {
    enable = true;
    mode = "installer";
    host = "chrysalis";
  };
  hardware.enableAllHardware = true;
  hardware.enableRedistributableFirmware = true;
  boot.kernelParams = [
    "console=tty0"
    "console=ttyS0,115200"
  ];
  boot.supportedFilesystems = [
    "btrfs"
    "vfat"
  ];
  boot.loader.efi.canTouchEfiVariables = false;
  documentation.nixos.enable = false;
  services.openssh.enable = false;
  environment.systemPackages = [
    pkgs.cryptsetup
    pkgs.btrfs-progs
    pkgs.nixos-install-tools
  ];
  virtualisation.diskSize = lib.mkDefault 8192;
}
