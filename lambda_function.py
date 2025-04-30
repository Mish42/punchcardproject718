import json
import boto3
import uuid
from google.oauth2 import id_token
from google.auth.transport import requests
from boto3.dynamodb.conditions import Key

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
                'body': json.dumps({'message': 'CORS preflight OK'})
            }

        if method == 'GET':
            response = table.query(
                KeyConditionExpression=Key('userId').eq(user_id)
            )
            tasks = response.get('Items', [])
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(tasks)
            }

        elif method == 'POST':
            body = json.loads(event.get('body', '{}'))
            project_id = body.get('projectId')
            project_desc = body.get('projectDesc')
            task_id = body.get('taskId')
            task_desc = body.get('taskDesc')

            if not all([project_id, project_desc, task_id, task_desc]):
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'All task and project fields are required'})
                }

            table.put_item(Item={
                'userId': user_id,
                'taskId': task_id,
                'projectId': project_id,
                'projectDesc': project_desc,
                'taskDesc': task_desc
            })

            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Task added'})
            }

        elif method == 'DELETE':
            body = json.loads(event.get('body', '{}'))
            project_id = body.get('projectId')
            task_id = body.get('taskId')

            if not project_id:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'Project ID is required'})
                }

            # Fetch all tasks for this user
            response = table.query(
                KeyConditionExpression=Key('userId').eq(user_id)
            )
            items = response.get('Items', [])

            if task_id:
                # Delete a single task with matching taskId and projectId
                matching_tasks = [
                    item for item in items
                    if item.get('projectId') == project_id and str(item.get('taskId')) == str(task_id)
                ]

                if not matching_tasks:
                    return {
                        'statusCode': 404,
                        'headers': cors_headers,
                        'body': json.dumps({'message': 'Task not found'})
                    }

                table.delete_item(
                    Key={
                        'userId': user_id,
                        'taskId': task_id
                    }
                )

                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({'message': 'Task deleted successfully'})
                }

            else:
                # Delete all tasks under the project
                deleted_count = 0
                for item in items:
                    if item.get('projectId') == project_id:
                        table.delete_item(
                            Key={
                                'userId': user_id,
                                'taskId': item['taskId']
                            }
                        )
                        deleted_count += 1

                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({'message': f'{deleted_count} task(s) deleted from project'})
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
