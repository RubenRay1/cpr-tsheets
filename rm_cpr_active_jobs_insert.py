import json
import pyodbc

# SQL Server connection
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=SVDW;"
    "DATABASE=CPR_RM;"
    "UID=pythonapps;"
    "PWD=bl@ckm0n;"
)
cursor = conn.cursor()


# ---- Truncate existing data
cursor.execute("TRUNCATE TABLE dbo.CPR_RM_AllJobs;")
conn.commit()
print("Truncated dbo.CPR_RM_AllJobs")


# ---- Get existing jobIds to avoid duplicates ----
cursor.execute("SELECT jobId FROM dbo.CPR_RM_AllJobs")
existing_job_ids = {row[0] for row in cursor.fetchall()}

#print(f"Existing jobIds in CPR_RM_AllJobs: {len(existing_job_ids)}")

# ---- Get table column names dynamically ----
cursor.execute("""
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'CPR_RM_AllJobs'
      AND TABLE_SCHEMA = 'dbo'
    ORDER BY ORDINAL_POSITION
""")
columns = [row[0] for row in cursor.fetchall()]

#print(f"Columns in CPR_RM_AllJobs ({len(columns)}): {columns}")

# Build INSERT statement dynamically
col_list = ", ".join(f"[{c}]" for c in columns)
param_list = ", ".join("?" for _ in columns)
insert_sql = f"""
    INSERT INTO dbo.CPR_RM_AllJobs ({col_list})
    VALUES ({param_list})
"""

# ---- Load JSON data ----
json_path = "cpr_all_jobs.json"  # adjust path if needed

with open(json_path, "r", encoding="utf-8") as f:
    raw = json.load(f)

# Handle different possible JSON shapes
if isinstance(raw, list):
    jobs = raw
elif isinstance(raw, dict):
    # adjust this if your JSON is wrapped differently
    jobs = raw.get("results") or raw.get("jobs") or []
else:
    jobs = []

#print(f"Total jobs in JSON: {len(jobs)}")

# ---- Filter to siteId == 8 and prepare rows ----
rows_to_insert = []
skipped_existing = 0
skipped_no_jobid = 0

for job in jobs:
    if not isinstance(job, dict):
        continue

    # Only jobs with siteId = 8
    if job.get("siteId") != 1:
        continue

    job_id = job.get("jobId")

    # Skip if no jobId present
    if job_id is None:
        skipped_no_jobid += 1
        continue

    # Skip duplicates
    if job_id in existing_job_ids:
        skipped_existing += 1
        continue

    # Build value list in the exact column order
    # If JSON doesn't have the key, .get() returns None -> inserts NULL
    values = [job.get(col) for col in columns]

    rows_to_insert.append(values)

print(f"Jobs to insert (siteId = 8, not already in table): {len(rows_to_insert)}")
#print(f"Skipped (no jobId): {skipped_no_jobid}")
#print(f"Skipped (already in table): {skipped_existing}")

# ---- Insert into SQL Server ----
inserted = 0

if rows_to_insert:
    cursor.executemany(insert_sql, rows_to_insert)
    inserted = len(rows_to_insert)  # count manually, not via rowcount
else:
    inserted = 0

conn.commit()
conn.close()

print(f"Inserted rows into dbo.CPR_RM_AllJobs: {inserted}")