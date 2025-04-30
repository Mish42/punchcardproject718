import json
import boto3
import uuid
from google.oauth2 import id_token
from google.auth.transport import requests

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Projects')

def lambda_handler(event, context):
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization', '')

    cors_headers = {
        'Access-Control-Allow-Origin': 'https://d1qgw2khdxi3ij.cloudfront.net',
        'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization'
    }

    if not auth_header.startswith('Bearer '):
        return {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Missing or invalid Authorization header'})
        }

    token = auth_header.split(' ')[1]

    try:
        request_adapter = requests.Request()
        data = id_token.verify_oauth2_token(
            token,
            request_adapter,
            '743162379253-7kjsr31h8tojhk38ng1ne8gqk60lt7io.apps.googleusercontent.com'
        )

        user_id = data.get('sub')
        method = event['httpMethod']

        if method == 'GET':
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
            )
            projects = response.get('Items', [])
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(projects)
            }

        elif method == 'POST':
            # Debug print to CloudWatch to inspect incoming data
            print("Event body:", event.get('body'))

            body = json.loads(event.get('body', '{}'))
            project_id = body.get('projectId')
            project_desc = body.get('projectDesc')
            task_id = body.get('taskId')
            task_desc = body.get('taskDesc')

            if not all([project_id, project_desc, task_id, task_desc]):
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'Project and task are required'})
                }

            table.put_item(Item={
                'userId': user_id,
                'projectId': project_id,
                'projectDesc': project_desc,
                'taskId': task_id,
                'taskDesc': task_desc
            })

            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Project and task added'})
            }

        else:
            return {
                'statusCode': 405,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Method Not Allowed'})
            }

    except Exception as e:
        print("Exception occurred:", str(e))
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Internal server error', 'error': str(e)})
        }

