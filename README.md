# Nxc systemd list


1. build the composition

```
# in nxc folder
nix develop --command nxc build -f g5k-nfs-store  
```

2. run the python script

```
# in the root folder
nix develop --command python3 main.py nxc/build/composition::g5k-nfs-store --output services_deps.json
```
