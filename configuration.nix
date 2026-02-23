{
  lib,
  nixpkgs,
  format,
  ...
}:
let
  old_pkgs = import (fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/nixos-24.05.tar.gz";
    sha256 = "0zydsqiaz8qi4zd63zsb2gij2p614cgkcaisnk11wjy3nmiq0x1s";
  }) { inherit system; };
  system = "x86_64-linux";
  pkgs = nixpkgs.legacyPackages.${system};
  python_env = pkgs.python312.withPackages (
    ps: with ps; [
      requests
    ]
  );
  # having python_env in app_pkgs might not work for the buildInputs its used in.
  app_pkgs = with pkgs; [
    python_env
    python312Packages.black
    old_pkgs.openssh
  ];
in
{
  config = {

    environment = {
      systemPackages = with pkgs; [
        neovim
        wget
        curl
        git
        file
        python_env
        python312Packages.black
        old_pkgs.openssh
      ];
      etc."test.py" = {
        # Source path is relative to the configuration.nix location in the repo
        source = ./main.py;
        # Set appropriate permissions
        mode = "0755";
        user = "master";
        group = "master";
      };
    };

    services.openssh = lib.mkForce {
      enable = true;
      package = old_pkgs.openssh;
      settings = {
        KexAlgorithms = [
          "curve25519-sha256"
          "curve25519-sha256@libssh.org"
          "diffie-hellman-group-exchange-sha256"
          "diffie-hellman-group16-sha512"
          "diffie-hellman-group18-sha512"
        ];
      };
    };
  }
}
