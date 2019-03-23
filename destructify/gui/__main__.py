import argparse
import importlib
import importlib.util
import pathlib

import destructify

parser = argparse.ArgumentParser("destructify.gui",
                                 description="Shows the Destructify GUI on a specified file and structure.")
parser.add_argument("structure", help="The class name of the structure you want to display.")
parser.add_argument("raw_data", help="The filename of the raw data.", type=pathlib.Path)
parser.add_argument("-f", help="The path of the file containing the structure.", type=pathlib.Path)

args = parser.parse_args()

if args.f:
    if not args.f.is_file():
        parser.error(f"The provided path {args.f} is not a valid file.")

    if "." in args.structure:
        module_name, class_name = args.structure.rsplit(".", 1)
    else:
        module_name = ""
        class_name = args.structure

    spec = importlib.util.spec_from_file_location(module_name, args.f)
    if spec is None:
        parser.error(f"The provided path {args.f} is not a valid Python file.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        Structure = getattr(module, class_name)
    except AttributeError:
        parser.error(f"The structure {class_name} could not be imported from {module}")

elif "." in args.structure:
    module_name, class_name = args.structure.rsplit(".", 1)
    try:
        Structure = getattr(importlib.import_module(module_name), class_name)
    except AttributeError:
        parser.error(f"The structure {class_name} could not be imported from {module_name}")
else:
    parser.error("The provided class path does not provide a full class path.")

if not args.raw_data.is_file():
    parser.error(f"The provided path {args.raw_data} is not a valid file.")

with open(args.raw_data, "rb") as f:
    destructify.gui.show(Structure, f)
