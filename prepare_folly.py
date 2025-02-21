from pathlib import Path
from zipfile import ZipFile
import requests
import sys
import platform
import os

current_directory = Path().absolute()

for arg in sys.argv:
    if arg.startswith("--folly-version="):
        custom_version = arg.split("=", 1).pop()
        break
else:
    custom_version = None

folly_source_filename = "folly-source-{version}.zip"
folly_python_path = current_directory / "folly"
folly_python_test_path = current_directory / "test"
folly_py_src_path = Path("./folly/python")

for folly_source_path in Path().glob("folly-source-*.zip"):
    version = folly_source_path.stem.removeprefix("folly-source-")
    if custom_version is None or version == custom_version:
        break
else:
    response = requests.get(
        "https://api.github.com/repos/facebook/folly/releases/{}".format(custom_version or "latest"),
        allow_redirects=False,
    )
    if response.status_code == 404:
        raise ValueError("Couldn't find any folly release named {}".format(response.url.rsplit("/", 1).pop()))
    assert response.status_code == 200, f"Unknown status reponse {response.status_code}"
    content = response.json()
    version = content["name"]
    for asset in content.get("assets") or []:
        if asset["content_type"] == "application/zip":
            break
    else:
        raise ValueError(f'Could not find any zip asset in version {version} of folly.')
    folly_source_path = current_directory / folly_source_filename.format(version=version)
    if folly_source_path.exists() is False:
        sys.stderr.write(f"# Downloading folly release {version} ...")
        sys.stderr.flush()
        zip_response = requests.get(asset["browser_download_url"], stream=True)
        with open(folly_source_path, "wb") as write:
            for item in zip_response.iter_content():
                write.write(item)
        sys.stderr.write(" Done\n")
        sys.stderr.flush()

if sys.platform == 'darwin':  # macOS
    if platform.machine() == 'arm64':  # Apple Silicon
        library_dirs = ['/opt/homebrew/lib']
        include_dirs = ['/opt/homebrew/include']
    else:  # Intel macOS
        library_dirs = ['/usr/lib']
        include_dirs = ['/usr/include']
elif sys.platform == 'win32':  # Windows
    library_dirs = ['C:\\Program Files\\Library\\lib']
    include_dirs = ['C:\\Program Files\\Library\\include']
elif sys.platform.startswith('linux'):  # Linux
    library_dirs = ['/usr/lib', '/usr/local/lib']
    include_dirs = ['/usr/include', '/usr/local/include']
else:  # Other platforms
    raise ValueError(f'Unknown {sys.platform=}')

for include_dir in include_dirs:
    if (Path(include_dir) / "folly").exists():
        break
else:
    raise FileNotFoundError( 'Could not find the include for folly in any '
                             'of the include directories:', include_dirs )


compile_args = ['-std=gnu++20', *([] if sys.version_info < (3, 13) else ['-D_Py_IsFinalizing=Py_IsFinalizing'])]


def copy_file_to(z: ZipFile, source: Path, destination: Path):
    if destination.parent.exists() is False:
        destination.parent.mkdir(parents=True)
    with open(destination, "wb") as write:
        write.write(z.read(str(source)))

def remove_recursive(path: Path, exclude_names: list = None):
    assert path.is_dir()
    for file in path.glob("**/*"):
        if file.is_dir():
            continue
        if exclude_names is None or file.name not in exclude_names:
            print(file)
            file.unlink()