import json
import boto3
import uuid
import urllib.request

# I was unable to get Lambda to work, for full transparency. The following is the attempt I had made to authenticate through google OAuth and then process user-specific project creation/deletion tasks
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Projects')

def lambda_handler(event, context):
    # Extract authorization header from incoming event
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization', '')

    # Checking authorization header
    if not auth_header.startswith('Bearer '):
        return {
            'statusCode': 401,
            'body': json.dumps({'message': 'Unauthorized'})
        }

    # Extract the token from header
    token = auth_header.split(' ')[1]
    token_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"

    try:
        # Validate token by calling Google's token info endpoint
        response = urllib.request.urlopen(token_url)
        data = json.load(response)

        if data.get('aud') != '743162379253-7kjsr31h8tojhk38ng1ne8gqk60lt7io.apps.googleusercontent.com':
            raise Exception("Invalid token audience")

        user_id = data.get('sub')  # Google unique user ID

        method = event['httpMethod']

        if method == 'GET':
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
            )
            projects = response.get('Items', [])
            return {
                'statusCode': 200,
                'body': json.dumps(projects)
            }

        elif method == 'POST':
            body = json.loads(event.get('body', '{}'))
            project_name = body.get('name')

            if not project_name:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'message': 'Project name required'})
                }

            project_id = str(uuid.uuid4())

            table.put_item(Item={
                'userId': user_id,
                'projectId': project_id,
                'name': project_name
            })

            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Project added'})
            }

        else:
            return {
                'statusCode': 405,
                'body': json.dumps({'message': 'Method Not Allowed'})
            }

    except Exception as e:
        return {
            'statusCode': 401,
            'body': json.dumps({'message': 'Invalid token', 'error': str(e)})
        }
