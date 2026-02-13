import time
import socket
import requests
import pyodbc
#import smtplib
#from email.message import EmailMessage
from requests.adapters import HTTPAdapter, Retry

ACCESS_TOKEN = "S.26__f15d80d08d8edefec27d2d4a906a5edd0038f81b"
JOBCODES_URL = "https://rest.tsheets.com/api/v1/jobcodes"
LOCATIONS_URL = "https://rest.tsheets.com/api/v1/locations"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Session with retries
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=5, connect=5, read=5,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504], # Retry on these HTTP status codes
            allowed_methods={"GET", "POST"},
        )
    ),
)


# POST with retries on DNS/connection errors
def post_with_retry(url, payload, max_retries=5, base_sleep=3):
    for attempt in range(1, max_retries + 1):
        try:
            return SESSION.post(url, json=payload, timeout=60)
        except (requests.exceptions.ConnectionError, socket.gaierror) as e:
            if attempt == max_retries:
                raise
            wait = base_sleep * attempt
            time.sleep(wait)


# Ensure that the value is a stripped string or empty
def _s(x):
    return "" if x is None else str(x).strip()


# Build full formatted address
def format_address(job):
    parts = [job["addr1"]]
    if job["addr2"]:
        parts.append(job["addr2"])
    city_state = ", ".join([p for p in [job["city"], job["state"]] if p])
    tail = " ".join([p for p in [city_state, job["zip"]] if p]).strip()
    return ", ".join([p for p in parts if p] + ([tail] if tail else []))


# Grab jobs from SQL Server and return list of dicts
def get_jobs_from_sql_server():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=SVDW;"
        "DATABASE=CPR_RM;"
        "UID=pythonapps;"
        "PWD=bl@ckm0n;"
    )
    cursor = conn.cursor()
    cursor.execute("""
        SELECT jobId, jobName, jobJobId,
               jobAddress1, jobAddress2, jobCity, jobStateCd, jobZip, JobFullAddress
        FROM CPR_RM.dbo.CPR_RM_AllJobs
        WHERE siteId = 1
            AND jobId IS NOT NULL
            AND jobName IS NOT NULL
            AND jobJobId IS NOT NULL
            AND jobStatus = 'Active'
            AND jobProgress IS NOT NULL
            AND jobProgress <> 'Paid in Full'
            AND ( jobProgress <> 'Not Sold/Lost' OR jobCreatedDate >= DATEADD(YEAR, -1, GETDATE()))      
        ORDER BY jobId DESC
    """)
    jobs = [{
        "job_id": _s(r.jobId),
        "job_name": _s(r.jobName),
        "job_number": _s(r.jobJobId),
        "addr1": _s(r.jobAddress1),
        "addr2": _s(r.jobAddress2),
        "city": _s(r.jobCity),
        "state": _s(r.jobStateCd),
        "zip": _s(r.jobZip),
        "JobFullAddress": _s(r.JobFullAddress),
        "country": "US",
    } for r in cursor.fetchall()]
    conn.close()
    return jobs


#Grab existing parent jobcodes from TSheets to avoid duplicates
def get_existing_parent_jobcodes():

    names = set()
    page = 1
    while True:
        r = SESSION.get(
            JOBCODES_URL,
            params={"page": page, "per_page": 200, "active": "true"},
            timeout=60,
        )
        r.raise_for_status()
        items = r.json().get("results", {}).get("jobcodes", {})
        if not items:
            break
        
        # Add job names to set
        names.update(
            jc["name"].strip()
            for jc in items.values()
            if jc.get("name")
        )
        # Check for more pages
        if r.json().get("more") or len(items) == 200:
            page += 1
        else:
            break
    
    return names


# Extract jobcode ID from JSON response
def extract_jobcode_id(resp_json):
    jc = resp_json.get("results", {}).get("jobcodes", {})
    if not jc:
        return None
    return next(iter(jc.values())).get("id")


# Create location and link to jobcode
def create_location_linked(job, jobcode_id):
    # Use existing formatted address if available
    formatted = job.get("JobFullAddress") or format_address(job)
    payload = {
        "data": [{
            "addr1": job["addr1"],
            "addr2": job["addr2"],
            "city":  job["city"],
            "state": job["state"],
            "zip":   job["zip"],
            "country": job["country"],
            "formatted_address": formatted,
            "active": True,
            "label": formatted, # using formatted address as label
            "linked_objects": {"jobcodes": [jobcode_id]}, # link to jobcode
        }]
    }
    return post_with_retry(LOCATIONS_URL, payload)


# Create parent jobcodes and optionally locations
def create_parent_jobcodes(jobs, existing_job_names, also_create_location=True):
    created_count = 0
    loc_created = 0

    for job in jobs:
        job_name = f"{job['job_number']}" #f"{job['job_name']} ({job['job_id']})"
        if job_name in existing_job_names:
            continue # skip existing jobcodes

        jc_payload = {
            "data": [{
                "name": job_name,
                "parent_id": 0,
                "active": True,
                "type": "regular",
                "assigned_to_all": True
            }]
        }

        jc_resp = post_with_retry(JOBCODES_URL, jc_payload)

        if jc_resp.status_code == 200:
            created_count += 1
            jobcode_id = extract_jobcode_id(jc_resp.json())

            # Create and link location if requested
            if also_create_location:
                l_resp = create_location_linked(job, jobcode_id)
                if l_resp.status_code == 200:
                    loc_created += 1


        elif jc_resp.status_code == 429:
            time.sleep(5)
            retry = post_with_retry(JOBCODES_URL, jc_payload)
            if retry.status_code == 200:
                created_count += 1
                jobcode_id = extract_jobcode_id(retry.json())

        if created_count and created_count % 25 == 0:
            time.sleep(2)
        else:
            time.sleep(0.75)

def main():
    jobs = get_jobs_from_sql_server()
    existing_job_names = get_existing_parent_jobcodes()
    create_parent_jobcodes(jobs, existing_job_names, also_create_location=True)


if __name__ == "__main__":
    main()
