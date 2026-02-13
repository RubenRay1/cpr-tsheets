# CPR TSheets Integration

Automated synchronization system between RM API and QuickBooks Time (formerly TSheets) for managing active job data.

## Overview

This system maintains real-time synchronization of active job data from RM to QuickBooks Time, ensuring that only current, active jobs are available in the time tracking system. The workflow automatically handles job creation, updates, and removal based on job status changes.

## System Architecture

```
RM API → SQL Database → QuickBooks Time API
   ↓           ↓              ↓
 JSON      Active Jobs    Export Table
           Table          (Comparison)
```

## Workflow Process

### 1. Data Retrieval
**Script:** `rm_cpr_data_retrieval.py`

Retrieves job data from the RM API and generates a JSON file containing all job information.

**Output:** `cpr_all_jobs.json`

### 2. Database Import
**Script:** `rm_cpr_active_jobs_insert.py`

Processes the JSON file and inserts active job records into the SQL database.

**Input:** `cpr_all_jobs.json`  
**Output:** Active jobs table in SQL database

### 3. QuickBooks Time Import
**Script:** `cpr_TSheetsImport.py`

Reads active jobs from the database and creates corresponding job entries in QuickBooks Time using the jobJobId and address fields.

**Input:** Active jobs table  
**Output:** Job entries in QuickBooks Time

### 4. QuickBooks Time Export
**Script:** `cpr_TSheetsExport.py`

Retrieves current job data from QuickBooks Time via API and stores it in a separate comparison table.

**Purpose:** Creates a snapshot of QuickBooks Time data for comparison against active jobs

**Output:** QuickBooks Time export table in SQL database

### 5. Inactive Job Removal
**Script:** `cpr_tsheets_remove_inactivejobs.py`

Compares the active jobs table with the QuickBooks Time export table to identify jobs that have been marked inactive. Automatically removes these jobs from QuickBooks Time.

**Frequency:** Monthly  
**Input:** Active jobs table + QuickBooks Time export table  
**Output:** Removal of inactive jobs from QuickBooks Time

### 6. Full Cleanup (Emergency Use Only)
**Script:** `cpr_tsheets_remove_all.py`

Removes all jobs from QuickBooks Time. This script should only be executed in exceptional circumstances requiring a complete system reset.

**Frequency:** As needed (rare)  
**Warning:** This will delete all job data from QuickBooks Time

## Execution Order

```
1. rm_cpr_data_retrieval.py
2. rm_cpr_active_jobs_insert.py
3. cpr_TSheetsImport.py
4. cpr_TSheetsExport.py
5. cpr_tsheets_remove_inactivejobs.py (monthly)
```

## Configuration

Environment variables are stored in `.env` (not tracked in git):
- RM API credentials
- SQL database connection strings
- QuickBooks Time API tokens

## Prerequisites

- Python 3.x
- Required Python packages (see requirements.txt)
- Access to RM API
- SQL database access
- QuickBooks Time API credentials

## Notes

- The system ensures only active jobs are visible in QuickBooks Time
- Inactive jobs are automatically removed to maintain data accuracy
- The comparison table approach enables efficient detection of status changes
- All sensitive credentials are stored in `.env` and excluded from version control
