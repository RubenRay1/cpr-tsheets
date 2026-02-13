import requests
import time

ACCESS_TOKEN = "S.26__f15d80d08d8edefec27d2d4a906a5edd0038f81b"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

JOBCODES_URL = "https://rest.tsheets.com/api/v1/jobcodes"


def get_all_jobcodes(per_page=200):
    jobcodes = {}
    page = 1

    while True:
        r = requests.get(
            JOBCODES_URL,
            headers=HEADERS,
            params={"page": page, "per_page": per_page},
            timeout=60,
        )
        r.raise_for_status()

        payload = r.json()
        data = payload.get("results", {}).get("jobcodes", {})
        if not data:
            break

        jobcodes.update(data)

        if not payload.get("more"):
            break

        page += 1

    return jobcodes


def deactivate_jobcode(jobcode_id: int):
    payload = {"data": [{"id": jobcode_id, "active": False}]}
    r = requests.put(JOBCODES_URL, headers=HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    #print("Fetching all jobcodes from TSheets...")
    jobcodes = get_all_jobcodes()
    #print(f"Found {len(jobcodes)} jobcodes total.\n")

    # Only those currently active
    active_jobcodes = []
    for jc_key, jc in jobcodes.items():
        try:
            jc_id = int(jc_key)
        except ValueError:
            continue

        if jc.get("active") is True:
            active_jobcodes.append((jc_id, jc.get("name", "")))

    print(f"Active jobcodes to deactivate: {len(active_jobcodes)}")

    if not active_jobcodes:
        print("No active jobcodes found. Exiting.")
        return

    updated = 0
    skipped = 0
    errors = 0

    # Tuning knobs
    throttle_seconds = 1.2     # small delay between requests
    max_retries = 5

    for i, (jc_id, name) in enumerate(active_jobcodes, start=1):
        print(f"[{i}/{len(active_jobcodes)}] Deactivating {jc_id} ('{name}')...")

        retries = max_retries
        while True:
            try:
                deactivate_jobcode(jc_id)
                updated += 1
                #print("  → Deactivated!")
                break

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else None

                if status == 429:
                    # Rate limit: backoff (increasing sleep each retry)
                    wait = 5 + (max_retries - retries) * 5
                    #print(f"  → Rate limited (429). Sleeping {wait}s then retrying...")
                    time.sleep(wait)
                    retries -= 1
                    if retries <= 0:
                        #print("  → Too many 429 retries. Marking as error and moving on.")
                        errors += 1
                        break
                    continue

                # Other HTTP errors
                print(f"  → ERROR {status}: {e}. Skipping.")
                errors += 1
                break

            except requests.RequestException as e:
                # Network / timeout / transient
                print(f"  → Request error: {e}. Skipping.")
                errors += 1
                break

        time.sleep(throttle_seconds)

    print("\n===============================================")
    print("TSHEETS DEACTIVATE ALL JOBCODES")
    print("===============================================")
    print(f"Total jobcodes found:            {len(jobcodes)}")
    print(f"Active jobcodes targeted:        {len(active_jobcodes)}")
    print(f"Successfully deactivated:        {updated}")
    print(f"Skipped (already inactive):      {len(jobcodes) - len(active_jobcodes)}")
    print(f"Errors:                          {errors}")
    print("Done.")
    print("===============================================")


if __name__ == "__main__":
    main()
