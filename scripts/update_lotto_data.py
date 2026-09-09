import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DATA_PATH = Path("lotto-data.json")
API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"


def fetch_draw(round_number):
    request = Request(
        API_URL.format(round_number),
        headers={
            "Accept": "application/json",
            "User-Agent": "lotto-data-updater/1.0",
        },
    )
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("returnValue") != "success":
        return None
    return {
        "numbers": sorted(payload[f"drwtNo{index}"] for index in range(1, 7)),
        "bonus": payload["bnusNo"],
    }


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    draws = {str(key): value for key, value in data.get("draws", {}).items()}
    next_round = max((int(key) for key in draws), default=1239) + 1
    added = 0

    while True:
        try:
            numbers = fetch_draw(next_round)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            print(f"새 회차 확인을 중단합니다: {error}")
            break
        if numbers is None:
            break
        draws[str(next_round)] = numbers
        added += 1
        next_round += 1
        time.sleep(0.2)

    DATA_PATH.write_text(
        json.dumps({"draws": draws}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"새 회차 {added}개 저장, 누적 회차 {len(draws)}개")


if __name__ == "__main__":
    main()
