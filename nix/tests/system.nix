{ self, pkgs }:
pkgs.testers.runNixOSTest {
  name = "chrysalis-terminal";
  nodes.machine = { lib, ... }: {
    imports = [ self.nixosModules.installer ];
    nix.enable = true;
    hardware.enableAllHardware = lib.mkForce false;
    hardware.enableRedistributableFirmware = lib.mkForce false;
    virtualisation.memorySize = 4096;
    virtualisation.cores = 2;
    virtualisation.diskSize = 16384;
    virtualisation.qemu.options = [ "-vga none -device virtio-gpu-pci" ];
    services.cage.environment.WLR_LIBINPUT_NO_DEVICES = "1";
    networking.networkmanager.ensureProfiles.profiles.acceptance = {
      connection = {
        id = "acceptance";
        type = "dummy";
        interface-name = "chry-net";
        autoconnect = true;
      };
      ipv4 = {
        method = "manual";
        address1 = "198.18.0.1/24";
      };
      ipv6.method = "disabled";
    };
  };
  testScript = ''
    def wait_for_pi():
        machine.wait_until_succeeds("su - chrysalis -c 'tmux list-panes -t chrysalis -F \"#{pane_current_command}\" | grep -xE \"pi|node|bun\"'")
        restarts = machine.succeed("systemctl show --value --property=NRestarts cage-tty1")
        machine.succeed("sleep 5")
        machine.succeed("systemctl is-active --quiet cage-tty1")
        machine.succeed("su - chrysalis -c 'tmux list-panes -t chrysalis -F \"#{pane_current_command}\" | grep -xE \"pi|node|bun\"'")
        assert machine.succeed("systemctl show --value --property=NRestarts cage-tty1") == restarts

    start_all()
    machine.wait_for_unit("cage-tty1.service")
    machine.wait_until_succeeds("pgrep -x ghostty")
    machine.wait_until_succeeds("su - chrysalis -c 'tmux has-session -t chrysalis'")
    wait_for_pi()
    machine.succeed("su - chrysalis -c '${pkgs.nodejs_24}/bin/node --import /etc/chrysalis/package/node_modules/tsx/dist/loader.mjs ${./runner.mts}'")
    machine.succeed("systemctl start getty@tty2.service")
    machine.wait_for_unit("getty@tty2.service")
    machine.succeed("su - chrysalis -c 'echo retained > /var/lib/chrysalis/state/acceptance-checkpoint'")
    machine.screenshot("terminal")
    machine.shutdown()
    machine.start()
    machine.wait_for_unit("cage-tty1.service")
    machine.succeed("grep retained /var/lib/chrysalis/state/acceptance-checkpoint")
    machine.wait_until_succeeds("su - chrysalis -c 'tmux has-session -t chrysalis'")
    wait_for_pi()
  '';
}
