import json
import boto3
import uuid
from boto3.dynamodb.conditions import Key
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

        if method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }

        if method == 'GET':
            response = table.query(
                KeyConditionExpression=Key('userId').eq(user_id)
            )
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(response.get('Items', []))
            }

        elif method == 'POST':
            body = json.loads(event.get('body', '{}'))
            project_id = body.get('projectId')
            project_desc = body.get('projectDesc')
            task_desc = body.get('taskDesc')

            if not project_id or not project_desc or not task_desc:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'Project ID, project description, and task description are required'})
                }

            task_id = str(uuid.uuid4().int)[:10]
            table.put_item(Item={
                'userId': user_id,
                'projectId': project_id,
                'projectDesc': project_desc,
                'taskDesc': task_desc,
                'taskId': task_id
            })

            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Task added'})
            }

        elif method == 'DELETE':
            body = json.loads(event.get('body', '{}'))
            project_id = body.get('projectId')
            task_desc = body.get('taskDesc')

            if not project_id:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'Project ID is required'})
                }

            # DOES NOT WORK PROPERLY - intended to delete entire queried project at once
            if not task_desc:
                response = table.query(
                    KeyConditionExpression=Key('userId').eq(user_id) & Key('projectId').eq(project_id)
                )
                for item in response.get('Items', []):
                    table.delete_item(Key={
                        'userId': item['userId'],
                        'projectId': item['projectId']
                    })
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'Project deleted'})
                }

            # DOES NOT WORK PROPERLY - intended to delete task from project 
            response = table.query(
                KeyConditionExpression=Key('userId').eq(user_id) & Key('projectId').eq(project_id)
            )
            for item in response.get('Items', []):
                if item.get('taskDesc') == task_desc:
                    table.delete_item(Key={
                        'userId': item['userId'],
                        'projectId': item['projectId']
                    })
                    break

            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Task deleted (if matched)'})
            }

        else:
            return {
                'statusCode': 405,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Method Not Allowed'})
            }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Internal server error', 'error': str(e)})
        }
