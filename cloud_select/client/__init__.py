#!/usr/bin/env python

# Copyright 2022 Lawrence Livermore National Security, LLC and other
# HPCIC DevTools Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (MIT)

import argparse
import os
import sys

import cloud_select
import cloud_select.main.cloud as cloud
import cloud_select.main.schemas as schemas
from cloud_select.logger import setup_logger


def add_instance_arguments(command):
    """
    Derive the attributes requested for an instance.
    """
    # All all options (based on type) except for command, which comes in "extra"
    for name, attrs in schemas.instance_properties.items():
        if name == "command":
            continue
        typ = attrs.get("type")

        # This is currently just envars, we will add separately as append args.
        if not typ and "oneOf" in attrs:
            continue

        choices = attrs.get("enum")
        default_type = str
        default = attrs.get("default")

        # It's either a string...
        if typ == "number" or "number" in typ:
            default_type = int
        elif typ == "boolean" or "boolean" in typ:
            default_type = bool
            default = None

        elif typ == "array":
            typ = attrs["items"]["type"]

            # Right now we have a list to select one thing from...
            if "enum" in attrs["items"]:
                choices = attrs["items"]["enum"]

        if default_type == bool:
            command.add_argument(
                f"--{name}",
                help=attrs.get("description") or f"The --{name} flag.",
                action=argparse.BooleanOptionalAction,  # THis ensures the default can be None
                default=default,
            )
        else:
            command.add_argument(
                f"--{name}",
                help=attrs.get("description") or f"The --{name} flag.",
                type=default_type,
                choices=choices,
                default=default,
            )


def get_parser():
    parser = argparse.ArgumentParser(
        description="Cloud Select",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Global Variables
    parser.add_argument(
        "--debug",
        dest="debug",
        help="use verbose logging to debug.",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--quiet",
        dest="quiet",
        help="suppress additional output.",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--verbose",
        dest="verbose",
        help="print additional solver output (atoms).",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--settings-file",
        dest="settings_file",
        help="custom path to settings file.",
    )

    parser.add_argument(
        "--cache-dir",
        dest="cache_dir",
        help="directory for data cache (defaults to ~/.cloud-select/cache).",
    )

    parser.add_argument(
        "--max-results",
        dest="max_results",
        help="Maximum results to return per cloud provider.",
        type=int,
    )
    parser.add_argument(
        "--cloud",
        dest="clouds",
        help="one or more clouds to include (if not provided, all are attempted).",
        choices=cloud.cloud_names,
        action="append",
        default=cloud.cloud_names,
    )

    parser.add_argument(
        "--cache-expire",
        dest="cache_expire",
        help="Expire the cache (and recreate) after this many hours (defaults to 168, one week). Set to 0 to not store a cache.",
        default=128,
    )

    # On the fly updates to config params
    parser.add_argument(
        "-c",
        dest="config_params",
        help=""""customize a config value on the fly to ADD/SET/REMOVE for a command
cloud-select -c set:key:value <command> <args>
cloud-select -c add:registry:/tmp/registry <command> <args>
cloud-select -c rm:registry:/tmp/registry""",
        action="append",
    )

    parser.add_argument(
        "--version",
        dest="version",
        help="show software version.",
        default=False,
        action="store_true",
    )

    subparsers = parser.add_subparsers(
        help="cloud_select actions",
        title="actions",
        description="actions",
        dest="command",
    )

    # print version and exit
    subparsers.add_parser("version", description="show software version")

    # Local shell with client loaded
    shell = subparsers.add_parser(
        "shell",
        description="shell into a Python session with a client.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    shell.add_argument(
        "--interpreter",
        "-i",
        dest="interpreter",
        help="python interpreter",
        choices=["ipython", "python", "bpython"],
        default="ipython",
    )

    # Install a known recipe from the registry
    instance = subparsers.add_parser(
        "instance",
        description="select an instance.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    instance.add_argument(
        "--json",
        help="dump output as json to terminal",
        default=False,
        action="store_true",
    )

    instance.add_argument(
        "--out-asp",
        dest="asp_out",
        help="Write ASP atoms to output file.",
    )

    instance.add_argument(
        "--out",
        dest="out",
        help="Write instances as json to output file.",
    )
    # Add attributes from spec
    add_instance_arguments(instance)
    return parser


def run():
    """
    run_cloud_select is the entrypoint to the singularity-hpc client.
    """

    parser = get_parser()

    def help(return_code=0):
        """print help, including the software version and active client
        and exit with return code.
        """

        version = cloud_select.__version__

        print("\nSingularity Registry (HPC) Client v%s" % version)
        parser.print_help()
        sys.exit(return_code)

    # If the user didn't provide any arguments, show the full help
    if len(sys.argv) == 1:
        help()

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()

    if args.debug is True:
        os.environ["MESSAGELEVEL"] = "DEBUG"

    # Show the version and exit
    if args.command == "version" or args.version:
        print(cloud_select.__version__)
        sys.exit(0)

    setup_logger(
        quiet=args.quiet,
        debug=args.debug,
    )

    # retrieve subparser (with help) from parser
    helper = None
    subparsers_actions = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    for subparsers_action in subparsers_actions:
        for choice, subparser in subparsers_action.choices.items():
            if choice == args.command:
                helper = subparser
                break

    # Does the user want a shell?
    if args.command == "instance":
        from .instance import main
    elif args.command == "config":
        from .config import main
    elif args.command == "shell":
        from .shell import main

    # Pass on to the correct parser
    return_code = 0
    try:
        main(args=args, parser=parser, extra=extra, subparser=helper)
        sys.exit(return_code)
    except UnboundLocalError:
        return_code = 1

    help(return_code)


if __name__ == "__main__":
    run()
