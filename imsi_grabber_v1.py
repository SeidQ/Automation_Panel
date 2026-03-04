import csv
import requests
import urllib3
from tkinter import Tk
from tkinter.filedialog import asksaveasfilename


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    "Authorization": "Basic bmV3Y3VzdG9tZXI6cmVtb3RzdWN3ZW4="
}

# CHANGE ONLY THIS PART  ↓
# ==============================
iccid_msisdn_list = {
"89994012401250949207": "994102586727",
"89994012401250949215": "994102586728"
}
# ==============================
fieldnames = [
    "Value", "Name", "Type", "Category", "ResourceStatus", "Description",
    "AdministrativeState", "OperationalState", "StartOperatingDate",
    "EndOperatingDate", "UsageState", "ResourceVersion", "lastModifiedStatusDate",
    "BatchId", "ResourceCharacteristic.name", "ResourceCharacteristic.value",
    "ResourceRelationship.relationshipType", "ResourceRelationship.resource.type",
    "ResourceRelationship.resource.value", "Place", "Note", "ActivationFeature",
    "Attachment", "RelatedParty", "ResourceSpecification"
]


def get_imsi(iccid):
    url = f"https://sfa-api.appazercell.prod/api/v1/simcard?number={iccid}"
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json().get("imsi")
    else:
        print(f"Error for ICCID {iccid}: {response.status_code}")
        return None


all_blocks = []

for iccid, msisdn in iccid_msisdn_list.items():
    imsi = get_imsi(iccid) or ""


    row_imsi = {field: "" for field in fieldnames}
    row_imsi["Value"] = imsi
    row_imsi["Name"] = "IMSI_number"
    row_imsi["Type"] = "IMSI"
    row_imsi["ResourceStatus"] = "available"
    row_imsi["StartOperatingDate"] = "2023-05-27T08:54:15.660Z"


    row_iccid = {field: "" for field in fieldnames}
    row_iccid["Value"] = iccid
    row_iccid["Name"] = "ICCID_number"
    row_iccid["Type"] = "ICCID"
    row_iccid["ResourceStatus"] = "available"
    row_iccid["StartOperatingDate"] = "2023-05-27T08:54:15.660Z"
    row_iccid["ResourceCharacteristic.name"] = "PIN;MySIM;PIN2;PUK;PUK2;Type"
    row_iccid["ResourceCharacteristic.value"] = "123A;True;876S;222A;987U;lte"
    row_iccid["ResourceRelationship.relationshipType"] = "dependency"
    row_iccid["ResourceRelationship.resource.type"] = "IMSI"
    row_iccid["ResourceRelationship.resource.value"] = imsi


    row_msisdn = {field: "" for field in fieldnames}
    row_msisdn["Value"] = msisdn or ""
    row_msisdn["Name"] = "MSIDN_number"
    row_msisdn["Type"] = "MSISDN"
    row_msisdn["ResourceStatus"] = "created"
    row_msisdn["StartOperatingDate"] = "2023-05-27T08:54:15.660Z"
    row_msisdn["ResourceCharacteristic.name"] = "Service Type;Customer Type;Usage Type;Public"
    row_msisdn["ResourceCharacteristic.value"] = "Postpaid;B2C;Voice;False"


    all_blocks.append(("header", fieldnames))
    all_blocks.append(("row", row_imsi))
    all_blocks.append(("row", row_iccid))
    all_blocks.append(("row", row_msisdn))
    all_blocks.append(("empty", None))

Tk().withdraw()
save_path = asksaveasfilename(
    initialfile="Create_Resource_22102025.csv",
    defaultextension=".csv",
    filetypes=[("CSV files", "*.csv")],
    title="Select folder to save file"
)

if save_path:
    with open(save_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for item_type, content in all_blocks:
            if item_type == "header":
                writer.writerow(content)
            elif item_type == "row":
                writer.writerow([content[field] for field in fieldnames])
            elif item_type == "empty":
                f.write("\n")
    print(f"File saved at: {save_path}")
else:
    print("Save cancelled by user.")
