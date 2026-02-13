import requests
import pyodbc

ACCESS_TOKEN = 'S.26__f15d80d08d8edefec27d2d4a906a5edd0038f81b'
BASE_URL = 'https://rest.tsheets.com/api/v1/jobcodes'
HEADERS = {'Authorization': f'Bearer {ACCESS_TOKEN}'}

# SQL Server Connection
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=SVDW;"
    "DATABASE=CPR_RM;"
    "UID=pythonapps;"
    "PWD=bl@ckm0n"
)
cursor = conn.cursor()

# 1. Clear existing data
#cursor.execute("TRUNCATE TABLE dbo.tblChildJobcodes;")
cursor.execute("DELETE FROM dbo.CPR_TSheets_Parentjobcodes;")
conn.commit()  # commit the truncates

# 2. Pull every page of jobcodes from TSheets
all_jobcodes = {}
page = 1

while True:
    response = requests.get(f"{BASE_URL}?per_page=200&page={page}", headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    jobcodes = data['results']['jobcodes']
    all_jobcodes.update(jobcodes)

    # Break if this was the last page
    if not data.get('more', False):
        break
    page += 1

# 3. Insert fresh data into SQL Server

parent_inserted = 0
#child_inserted = 0

# Insert parents
for jc in all_jobcodes.values():
    if jc['parent_id'] == 0:
        location_id = jc['locations'][0] if jc.get('locations') else None
        cursor.execute(
            """
            INSERT INTO dbo.CPR_TSheets_Parentjobcodes
                (id, name, active, type, created, hasChildren, locationId)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            jc['id'],
            jc['name'],
            int(jc['active']),
            jc['type'],
            jc['created'],
            int(jc['has_children']),
            location_id
        )
        parent_inserted += 1

# Insert children
# for jc in all_jobcodes.values():
#     if jc['parent_id'] != 0:
#         location_id = jc['locations'][0] if jc.get('locations') else None
#         cursor.execute(
#             """
#             INSERT INTO dbo.tblChildJobcodes
#                 (id, name, active, parentId, assignedToAll, locationId, created)
#             VALUES (?, ?, ?, ?, ?, ?, ?)
#             """,
#             jc['id'],
#             jc['name'],
#             int(jc['active']),
#             jc['parent_id'],
#             int(jc['assigned_to_all']),
#             location_id,
#             jc['created']
#         )
#         child_inserted += 1

conn.commit()
conn.close()

print(f"Inserted into CPR_TSheets_Parentjobcodes: {parent_inserted}")
#print(f"Inserted into tblChildJobcodes: {child_inserted}")
