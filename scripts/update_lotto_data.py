import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DATA_PATH = Path("lotto-data.json")
API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"
ARCHIVE_URL = "https://raw.githubusercontent.com/ParkMinKyu/bok/master/lottoHistory.json"


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
    return sorted(payload[f"drwtNo{index}"] for index in range(1, 7))


def fetch_archive():
    request = Request(
        ARCHIVE_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "lotto-data-updater/1.0",
        },
    )
    with urlopen(request, timeout=30) as response:
        archive = json.loads(response.read().decode("utf-8"))

    if not isinstance(archive, list) or not archive:
        raise ValueError("공개 당첨 이력에서 유효한 회차 목록을 받지 못했습니다.")

    draws = {}
    for draw in archive:
        round_number = int(draw["drwNo"])
        numbers = sorted(int(draw[f"drwtNo{index}"]) for index in range(1, 7))
        if len(set(numbers)) != 6 or any(number < 1 or number > 45 for number in numbers):
            raise ValueError(f"{round_number}회 당첨번호 데이터가 올바르지 않습니다.")
        draws[str(round_number)] = numbers

    rounds = sorted(int(round_number) for round_number in draws)
    if rounds != list(range(1, rounds[-1] + 1)):
        raise ValueError("공개 당첨 이력에 누락 회차가 있어 갱신을 중단합니다.")
    return draws


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    draws = {str(key): value for key, value in data.get("draws", {}).items()}
    archived_draws = fetch_archive()
    added = len(set(archived_draws) - set(draws))
    draws.update(archived_draws)
    next_round = max((int(key) for key in draws), default=0) + 1

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
        json.dumps(
            {
                "source": ARCHIVE_URL,
                "draws": dict(sorted(draws.items(), key=lambda item: int(item[0]))),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"이력 반영 및 새 회차 {added}개 저장, 누적 회차 {len(draws)}개")


if __name__ == "__main__":
    main()
