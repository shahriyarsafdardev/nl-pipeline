from s3 import read_object, upload_object
from logger import getLogger
import json
import io

logger = getLogger()


def compare_lowcode_endpoints(filename, local=False):
    lowcode_connectors = []

    if local:
        with open(filename, 'r') as f:
            connectors = json.load(f)
    else:
        file_content = read_object(filename)
        connectors = json.loads(file_content)

    for connector in connectors:
        if connector['airbyte_status'] != 'lowcode-connector':
            logger.info(f"Skipping {connector['name']}, not a lowcode connector")
            continue

        # makes sure that the list of Airbyte existing endpoints exists
        if not connector.get('existing_airbyte_endpoints', None):
            logger.info(f"{connector['name']} does not have a list of existing Airbyte endpoints")
            continue

        # makes sure that the list of Sphere endpoints exists
        if not connector.get('sphere_endpoints', None):
            logger.info(f"{connector['name']} does not have a list of Sphere endpoints")
            continue

        logger.info(f"{connector['name']} has {len(connector['sphere_endpoints'])} Sphere Endpoints")
        logger.info(f"{connector['name']} has {len(connector['existing_airbyte_endpoints'])} Existing Airbyte Endpoints")
        
        # perform comparison
        common_endpoints = []

        logger.info(f"Extracting common endpoints for {connector['name']}")
        # Check if both 'existing_airbyte_endpoints' and 'sphere_endpoints' exist in the connector
        if 'existing_airbyte_endpoints' in connector and 'sphere_endpoints' in connector:
            # For each airbyte endpoint, check if it is included in any sphere endpoint
            for airbyte_endpoint in connector['existing_airbyte_endpoints']:
                for sphere_endpoint in connector['sphere_endpoints']:
                    if airbyte_endpoint in sphere_endpoint:
                        common_endpoints.append(airbyte_endpoint)
                        break  # Break out of the inner loop if a match is found

        connector['common_endpoints'] = common_endpoints
        connector['common_endpoint_count'] = len(common_endpoints)

        logger.info(f"Found {len(connector['common_endpoints'])} common endpoints for {connector['name']}")

        # add this connector to a new list of connectors
        lowcode_connectors.append(connector)

    logger.info(f"Writing connectors to json file")
    if local:
        with open('lowcode_connectors_comparison.json', 'w') as f:
            json.dump(lowcode_connectors, f, indent=4)
    else:
        updated_connectors = json.dumps(connectors, indent=4)
        file_obj = io.BytesIO(updated_connectors.encode('utf-8'))
        upload_object(file_obj, filename, extraArgs={'CacheControl': 'no-store'})


if __name__ == "__main__":
    compare_lowcode_endpoints('airbyte_connectors.json', local=True)