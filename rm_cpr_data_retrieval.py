import requests, base64, json, os

# Determine directory where THIS script lives
script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir,"cpr_all_jobs.json")

# define customer database and product
dbname = "cprinc"
product = "restorationmanager"

# define username, password, and ApiSecret (should probably store in file or environmental variables instead)
UN = "ryanez@bmsmanagement.com"
PW = "RYanez2025"
secret = "12b55822-a7a4-4e02-a327-d189f918f3fd"

# creates URLs
baseURL = "https://"+dbname+"."+product+".net"
loginURL = baseURL + "/api/login"
testURL = baseURL + "/api/Login/decryptedtoken"
rundate = "2014-12-22T00:00:00Z"

# prepares username and password in base64 for header
userpass = "{username: '"+ UN +"', password: '"+ PW +"'}"
userpass64 = base64.b64encode(userpass.encode("ascii")).decode("ascii")

# sends POST request to loginURL with base64 credentials in header
# gets back token to be used for subsequent request headers along with the API Secret
loginResponse = requests.post(url=loginURL, headers={"Authorization": "Basic %s" % userpass64})
token = loginResponse.content.decode("ascii").replace('"','')
headers = {"Token": "%s" % token, "ApiSecret": "%s" % secret}
print(loginResponse)

jFilter = "?includeRelatedData=false&ModifiedSince=" + rundate

# call Jobs API and store results as json
jobURL = baseURL + "/api/Jobs" + jFilter
jobResponse = requests.get(url= jobURL, headers=headers)

# Convert response to JSON
jobJson = jobResponse.json()

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(jobJson, f, ensure_ascii=False, indent=4)
