import requests
from pathlib import Path
from time import sleep

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
OUTPUT_DIR = Path("yellow_tripdata")
OUTPUT_DIR.mkdir(exist_ok=True)


def download_file(url: str, output_path: Path, retries: int = 3):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=headers, stream=True, timeout=30)

            if r.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                print(f"[OK] {output_path.name}")
                return True

            elif r.status_code in (403, 404):
                print(f"[SKIP {r.status_code}] {url}")
                return False

            else:
                print(f"[WARN {r.status_code}] retry {attempt}/{retries}")
                sleep(2)

        except requests.RequestException as e:
            print(f"[ERROR] {e} retry {attempt}/{retries}")
            sleep(2)

    print(f"[FAIL] {url}")
    return False


def main():
    for year in (2024, 2025):
        for month in range(1, 13):
            filename = f"yellow_tripdata_{year}-{month:02d}.parquet"
            url = f"{BASE_URL}/{filename}"
            output_path = OUTPUT_DIR / filename

            if output_path.exists():
                print(f"[EXISTS] {filename}")
                continue

            download_file(url, output_path)


if __name__ == "__main__":
    main()
