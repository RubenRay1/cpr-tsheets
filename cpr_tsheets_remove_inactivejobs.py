import requests
import time
import pyodbc

ACCESS_TOKEN = "S.26__f15d80d08d8edefec27d2d4a906a5edd0038f81b"
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

JOBCODES_URL = "https://rest.tsheets.com/api/v1/jobcodes"


# Get all jobcodes with pagination
def get_all_jobcodes():
    jobcodes = {}
    page = 1
    while True:
        r = requests.get(
            JOBCODES_URL,
            headers=HEADERS,
            params={"page": page, "per_page": 200},
        )
        r.raise_for_status()
        data = r.json().get("results", {}).get("jobcodes", {})
        if not data:
            break

        jobcodes.update(data)

        if not r.json().get("more"):
            break
        page += 1

    return jobcodes


# Update a jobcode’s active flag to False
def deactivate_jobcode(jobcode_id: int):
    payload = {
        "data": [
            {
                "id": jobcode_id,
                "active": False,
            }
        ]
    }
    r = requests.put(JOBCODES_URL, headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()


def main():
    # SQL: get list of jobcode IDs from view
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=SVDW;"
        "DATABASE=CPR_RM;"
        "UID=pythonapps;"
        "PWD=bl@ckm0n;"
        #"Trusted_Connection=yes;"

    )
    cursor = conn.cursor()

    # View contains the CPR parent jobcodes that should be inactive in TSheets
    cursor.execute("SELECT id FROM dbo.CPR_RM_InactiveJobs")
    inactive_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Make it a set for fast lookup
    inactive_ids_set = set(inactive_ids)

    print(f"Inactive jobcodes from view (CPR_RM_InactiveJobs): {len(inactive_ids_set)}")

    if not inactive_ids_set:
        print("No inactive jobcodes found in view. Exiting.")
        return

    # TSheets: pull all jobcodes
    print("Fetching all jobcodes from TSheets...")
    jobcodes = get_all_jobcodes()
    print(f"Found {len(jobcodes)} jobcodes in TSheets.\n")

    # Filter & deactivate
    to_deactivate = 0
    updated = 0
    errors = 0

    # jobcodes dict keys are strings ("12345"), values are jobcode dicts
    for jc_key, jc in jobcodes.items():
        try:
            jc_id = int(jc_key)
        except ValueError:
            continue

        # Only care about jobcodes whose ID is in the view
        if jc_id not in inactive_ids_set:
            continue

        name = jc.get("name", "")
        active_status = jc.get("active", False)

        # Only deactivate those currently active
        if not active_status:
            print(f"Jobcode {jc_id} ('{name}') is already inactive. Skipping.")
            continue

        to_deactivate += 1
        print(f"Deactivating jobcode {jc_id} ('{name}')...")

        success = False
        retries = 3

        while not success and retries > 0:
            try:
                deactivate_jobcode(jc_id)
                success = True
                updated += 1
                print("  → Deactivated!")
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code
                if status == 429:
                    print("  → Rate limited (429). Sleeping 5 seconds and retrying...")
                    time.sleep(5)
                    retries -= 1
                else:
                    print(f"  → ERROR {status}: {e}. Skipping this jobcode.")
                    errors += 1
                    break

        # small throttle between requests
        time.sleep(1.5)

    print("\n===============================================")
    print("TSHEETS LAX INACTIVE JOBCODE DEACTIVATION")
    print("===============================================")
    print(f"Jobcodes from view (total):      {len(inactive_ids_set)}")
    print(f"Matched & currently active:      {to_deactivate}")
    print(f"Successfully deactivated:        {updated}")
    print(f"Errors:                          {errors}")
    print("Done.")
    print("===============================================")


if __name__ == "__main__":
    main()
