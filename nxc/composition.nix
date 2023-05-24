{ pkgs, ... }: {
  roles = {
    foo = { pkgs, ... }:
      {
        services.nginx = {
          enable = true;
          # a minimal site with one page
          virtualHosts.default = {
            root = pkgs.runCommand "testdir" { } ''
              mkdir "$out"
              echo hello world > "$out/index.html"
            '';
          };
        };
        networking.firewall.enable = false;

        # add needed package
        # environment.systemPackages = with pkgs; [ socat ];
        # services.openssh.enable = true;
      };
  };
  testScript = ''
    foo.succeed("true")
  '';
}
