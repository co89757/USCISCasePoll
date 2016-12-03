# USCIS Case Status Polling

This is a simple python script to poll USCIS case status and optionally generate email alert on status change.
The core script is `poll_uscis.py`

# Usage
## Setup
To set up the environment for the python script, in the repo directory, do

```sh
# do this in your virtualenv or normal terminal with sudo
>pip install -r requirements.txt
```

## Run script

Before you run the script, it's highly helpful to take a quick look at the manual

```sh
python poll_uscis.py -h
```

The only mandatory argument to the script is obviously your USCIS case receipt number, so a simple run looks like:

```sh
## simple run with minimal information including status, and days elapsed since received
python poll_uscis.py -c <your_case_number>
## request detail text on status as well
python poll_uscis.py -c <casenumber> -d/--detail
## send email alert
python poll_uscis.py -c <casenumber> --mailto <comma-separated-emails>
```
