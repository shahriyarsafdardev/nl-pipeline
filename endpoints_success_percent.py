import io
from s3 import read_object, upload_object
from logger import getLogger
import json

logger = getLogger()


def get_endpoints_success_percent(filename, airbyte_status, local=False):
    """
    Function to calculate the success percentage between 'common_endpoints' and 
    'airbyte_endpoints' of each connector in the provided file if the connector's 
    'airbyte_status' matches the given status. 

    It checks success percent of the created endpoints.

    Args:
        file_path (str): Path to the input JSON file.
        airbyte_status (str): The airbyte status to filter the connectors.
        local (bool): Flag to read the file from local or s3.

    Returns:
        None
    """

    connectors_list = []
    total_airbyte_endpoints = 0
    total_common_endpoints = 0

    if local:
        with open(filename, 'r') as f:
            connectors = json.load(f)
    else:
        file_content = read_object(filename)
        connectors = json.loads(file_content)

    # Iterate over each connector
    for connector in connectors:
        if connector['airbyte_status'] != airbyte_status:
            logger.info(f"Skipping {connector['name']}, not a lowcode connector")
            continue

        # makes sure that the list of Airbyte existing endpoints exists
        if not 'existing_airbyte_endpoints' in connector:
            logger.info(f"{connector['name']} does not have a list of existing Airbyte endpoints")
            continue
        
        # makes sure that the list of Common endpoints exists
        if not 'common_endpoints' in connector:
            logger.info(f"{connector['name']} does not have a list of Common endpoints")
            continue

        logger.info(f"Calculating endpoints Success Percentage for {connector['name']}")

        # Check if both 'existing_airbyte_endpoints' and 'common_endpoints' exist in the connector
        if 'existing_airbyte_endpoints' in connector and 'common_endpoints' in connector:
            total_airbyte_endpoints = total_airbyte_endpoints + len(connector['existing_airbyte_endpoints'])
            total_common_endpoints = total_common_endpoints + len(connector['common_endpoints'])
            success_percentage = round((len(connector['common_endpoints']) / len(connector['existing_airbyte_endpoints'])) * 100, 2) if len(connector['existing_airbyte_endpoints']) != 0 else len(connector['common_endpoints'])
            connectors_list.append({"name": connector['name'], "endpoint_success_percentage": success_percentage})

            logger.info(f"Endpoints Success percentage for {connector['name']}: {success_percentage}")

    overall_success_percentage = round((total_common_endpoints / total_airbyte_endpoints) * 100, 2) if total_airbyte_endpoints != 0 else total_common_endpoints
    logger.info(f"Overall Endpoints Success percentage: {overall_success_percentage}")
    
    if local:
        with open('lowcode_connectors_success_percentage.json', 'w') as f:
            json.dump({"overall_endpoint_success_percentage": overall_success_percentage, "connectors": connectors_list}, f, indent=4)
    else:
        updated_connectors = json.dumps({"overall_endpoint_success_percentage": overall_success_percentage, "connectors": connectors_list}, indent=4)
        file_obj = io.BytesIO(updated_connectors.encode('utf-8'))
        upload_object(file_obj, 'lowcode_connectors_success_percentage.json', extraArgs={'CacheControl': 'no-store'})



get_endpoints_success_percent('lowcode_connectors_comparison.json', 'lowcode-connector', True)