import zipfile
import requests
import os
import shutil
from pathlib import Path

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Priority": "u=0, i",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
}

def main():
    url = "https://api.github.com/repos/facebook/folly/releases/"
    url += f"tags/{custom_version}" if (custom_version := os.getenv("FOLLY_VERSION")) else "latest"
    response = requests.get(
        url, headers={"Authorization": f"Bearer {token}"} if (token := os.environ.get("GITHUB_TOKEN")) else {}
    )
    print("Queried API")
    response.raise_for_status()
    content = response.json()
    version = content["name"]
    for asset in content.get("assets") or []:
        if asset["content_type"] == "application/zip":
            break
    else:
        raise ValueError(f'Could not find any zip asset in version {version} of folly.')
    print(f"Found version {version}")

    folly_source_path = Path(f"./folly-source-{version}").absolute()
    if folly_source_path.exists():
        shutil.rmtree(folly_source_path)
    folly_source_path.mkdir()

    compressed_folly_source_path = folly_source_path.parent / (folly_source_path.name + ".zip")
    print("Downloading folly")
    try:
        downloaded = False
        zip_response = requests.get(asset["browser_download_url"], stream=True)
        with open(compressed_folly_source_path, "wb") as write:
            for item in zip_response.iter_content():
                write.write(item)
        downloaded = True
        print("Downloading done")
    finally:
        if downloaded is False:
            print("Downloading failed")
    with zipfile.ZipFile(compressed_folly_source_path) as z:
        z.extractall(folly_source_path)
    compressed_folly_source_path.unlink()
    print(f"Decompressed as {folly_source_path}")

    for source_path in Path("insertions").glob("**/*"):
        if source_path.name == "README.md" or source_path.is_dir():
            continue
        with open(source_path, "rb") as read:
            content = read.read()
        destination = Path(folly_source_path, source_path.relative_to("insertions")).absolute()
        with open(destination, "wb") as write:
            write.write(content)
        print(f"Replaced {destination} by {source_path}")
        
if __name__ == "__main__":
    main()