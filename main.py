import json
import argparse
import os
from os import listdir
from os.path import isfile, join
from pathlib import Path
import re
import subprocess

def get_init_by_role(filename):
    init_by_role = {}
    with open(filename, "r") as f:
        json_data = json.load(f)
        for role_name, role_data in json_data["compositions_info"]["composition"]["roles"].items():
            init_by_role[role_name] = role_data["init"]
    return init_by_role
    
def get_list_services(init_path):
    etc_path = os.path.join(init_path, "etc")
    services_path = os.path.realpath(os.path.join(etc_path, "systemd/system"))
    return [os.path.realpath(os.path.join(services_path, service)) for service in os.listdir(services_path) if service[-8:] == ".service"]
    
def extract_exec_start_from_config(service_config_path):
    binaries = set()
    myregex = re.compile("Exec(Start|Reload)=")
    nix_store_regex = re.compile("[-@!]*/nix/store/")
    with open(service_config_path, "r") as config_path:
        for line in config_path:
            if len(line) > 0:
                matches = myregex.match(line)
                if matches:
                    exec_command = line[matches.end():]
                    binary = exec_command.strip().split(" ")[0]
                    matches2 = nix_store_regex.match(binary)
                    if matches2:
                        binary_nix_store_path = binary[matches2.end() - 11:] 
                        binaries.add(binary_nix_store_path)
    return binaries


def read_rpath_variable(binary_path):
    objdump_process = subprocess.run(["objdump", "-x", binary_path], capture_output=True)
    runpath_regex = re.compile("RUNPATH")
    for line in objdump_process.stdout.decode().split("\n"):
        matches = runpath_regex.match(line.strip())
        if matches:
            return line.split()[1]
    return None
    
def get_list_of_needed_libs(binary_path):
    ldd_process = subprocess.run(["ldd", binary_path], capture_output=True)
    lines = ldd_process.stdout.decode().split("\n")
    return [line.split(" => ")[0].strip() for line in lines if len(line) > 0] 

def get_paths_to_copy(service, max_depth=1):
    if max_depth == 0:
        return set()
    output = subprocess.run(["nix-store", "-qR", service], capture_output=True)
    dependencies = set()
    for dep_path in output.stdout.decode().splitlines():
        if dep_path not in dependencies:
            dependencies.add(dep_path)
            dependencies = dependencies.union(get_paths_to_copy(dep_path, max_depth-1))
    return dependencies


def main():
    parser = argparse.ArgumentParser(description="Get the dependencies of the services of a nxc composition")
    parser.add_argument('build_result', help='JSON resulting of nxc build')
    parser.add_argument('--output', '-o', help='where to store the resulting JSON. stdout if none')

    args = parser.parse_args()
    
    # open result build
    json_file = args.build_result

    # get the init field of each role
    init_by_role = get_init_by_role(json_file)
    
    services_deps_by_role = {}

    # then go to etc/systemd/system
    for role, init_path in init_by_role.items():
        services_deps_by_role[role] = {}
        # all the services finish in .service
        services_list = get_list_services(init_path[:-5])
        binaries = set()
        for service_config in services_list:
            service_name = service_config.split("/")[-1]
            services_deps_by_role[role][service_name] = {}
            services_deps_by_role[role][service_name]["store"] = list(get_paths_to_copy(service_config))
            # read the config for `ExecStart`
            # extract the binary
            binaries = extract_exec_start_from_config(service_config)

            for binary in binaries:
                binary_name_short = binary.split("/")[-1]
                services_deps_by_role[role][service_name][binary_name_short] = {}

                # get the objdump -x BIN | grep RUNPATH
                rpath = read_rpath_variable(binary)
                if rpath:
                    services_deps_by_role[role][service_name][binary_name_short]["RPATH"] = rpath.split(":")

                # get ldd of BIN
                ldd = get_list_of_needed_libs(binary)
                if len(ldd) > 0:
                    services_deps_by_role[role][service_name][binary_name_short]["ldd"] = ldd
            
            
    if args.output:
        with open(args.output, "w") as output_file:
            json.dump(services_deps_by_role, output_file)
    else:
        print(json.dumps(services_deps_by_role))
    return 0
    
    
if __name__ == "__main__":
    main()
