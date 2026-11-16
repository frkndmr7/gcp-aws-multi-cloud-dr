from typing import Any

from botocore.exceptions import ClientError

from app.models import URLRecord


class DynamoDBRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def create_if_absent(self, record: URLRecord) -> bool:
        try:
            self._table.put_item(
                Item=record.model_dump(mode='json'),
                ConditionExpression='attribute_not_exists(#id)',
                ExpressionAttributeNames={'#id': 'id'},
            )
        except ClientError as exc:
            if exc.response.get('Error', {}).get('Code') == 'ConditionalCheckFailedException':
                return False
            raise
        return True

    def get_by_id(self, code: str) -> URLRecord | None:
        item = self._table.get_item(Key={'id': code}, ConsistentRead=True).get('Item')
        if item is None:
            return None
        record = URLRecord.model_validate(item)
        if record.id != code:
            raise ValueError('DynamoDB item ID does not match requested ID')
        return record
