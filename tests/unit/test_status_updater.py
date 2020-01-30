import boto3
import pytest
from botocore.exceptions import ClientError
from mock import patch, Mock

from backend.lambdas.jobs.status_updater import update_status, determine_status, job_has_errors

pytestmark = [pytest.mark.unit, pytest.mark.jobs]


@patch("backend.lambdas.jobs.status_updater.job_has_errors", Mock(return_value=False))
def test_it_determines_basic_statuses():
    assert "FIND_FAILED" == determine_status("123", "FindPhaseFailed")
    assert "FORGET_FAILED" == determine_status("123", "ForgetPhaseFailed")
    assert "FAILED" == determine_status("123", "Exception")
    assert "RUNNING" == determine_status("123", "JobStarted")
    assert "COMPLETED" == determine_status("123", "JobSucceeded")


@patch("backend.lambdas.jobs.status_updater.job_has_errors", Mock(return_value=True))
def test_it_determines_completed_with_errors():
    assert "COMPLETED_WITH_ERRORS" == determine_status("123", "JobSucceeded")


@patch("backend.lambdas.jobs.status_updater.table")
def test_it_determines_job_has_errors_for_failed_object_updates(table):
    table.get_item.return_value = {
        "Item": {
            "TotalObjectUpdateFailedCount": 1
        }
    }
    assert job_has_errors("test")


@patch("backend.lambdas.jobs.status_updater.table")
def test_it_determines_job_has_errors_for_failed_queries(table):
    table.get_item.return_value = {
        "Item": {
            "TotalQueryFailedCount": 1
        }
    }
    assert job_has_errors("test")


@patch("backend.lambdas.jobs.status_updater.table")
def test_it_determines_job_has_errors_for_failed_object_updates(table):
    table.get_item.return_value = {
        "Item": {
            "TotalObjectUpdateFailedCount": 0,
            "TotalQueryFailedCount": 0,
        }
    }
    assert not job_has_errors("test")


@patch("backend.lambdas.jobs.status_updater.determine_status", Mock(return_value="RUNNING"))
@patch("backend.lambdas.jobs.status_updater.table")
def test_it_handles_job_started(table):
    update_status("job123", [{
        "Id": "job123",
        "Sk": "123456",
        "Type": "JobEvent",
        "CreatedAt": 123.0,
        "EventName": "JobStarted",
        "EventData": {}
    }])
    table.update_item.assert_called_with(
        Key={
            'Id': "job123",
            'Sk': "job123",
        },
        UpdateExpression="set #JobStatus = :JobStatus, #JobStartTime = :JobStartTime",
        ConditionExpression="#Id = :Id AND #Sk = :Sk AND (#JobStatus = :RUNNING OR #JobStatus = :QUEUED)",
        ExpressionAttributeNames={
            "#Id": "Id",
            "#Sk": "Sk",
            '#JobStatus': 'JobStatus',
            '#JobStartTime': 'JobStartTime',
        },
        ExpressionAttributeValues={
            ":Id": "job123",
            ":Sk": "job123",
            ':RUNNING': 'RUNNING',
            ':QUEUED': 'QUEUED',
            ':JobStatus': "RUNNING",
            ':JobStartTime': 123.0,
        },
        ReturnValues="UPDATED_NEW"
    )
    assert 1 == table.update_item.call_count


@patch("backend.lambdas.jobs.status_updater.determine_status", Mock(return_value="COMPLETED"))
@patch("backend.lambdas.jobs.status_updater.table")
def test_it_handles_job_finished(table):
    update_status("job123", [{
        "Id": "job123",
        "Sk": "123456",
        "Type": "JobEvent",
        "CreatedAt": 123,
        "EventName": "JobSucceeded",
        "EventData": {}
    }])
    table.update_item.assert_called_with(
        Key={
            'Id': "job123",
            'Sk': "job123",
        },
        UpdateExpression="set #JobStatus = :JobStatus, #JobFinishTime = :JobFinishTime",
        ConditionExpression="#Id = :Id AND #Sk = :Sk AND (#JobStatus = :RUNNING OR #JobStatus = :QUEUED)",
        ExpressionAttributeNames={
            "#Id": "Id",
            "#Sk": "Sk",
            '#JobStatus': 'JobStatus',
            '#JobFinishTime': 'JobFinishTime',
        },
        ExpressionAttributeValues={
            ":Id": "job123",
            ":Sk": "job123",
            ':RUNNING': 'RUNNING',
            ':QUEUED': 'QUEUED',
            ':JobStatus': "COMPLETED",
            ':JobFinishTime': 123.0,
        },
        ReturnValues="UPDATED_NEW"
    )
    assert 1 == table.update_item.call_count


@patch("backend.lambdas.jobs.status_updater.determine_status", Mock(return_value="FIND_FAILED"))
@patch("backend.lambdas.jobs.status_updater.table")
def test_it_handles_find_failed(table):
    update_status("job123", [{
        "Id": "job123",
        "Sk": "123456",
        "Type": "JobEvent",
        "CreatedAt": 123.0,
        "EventName": "FindPhaseFailed",
        "EventData": {}
    }])
    table.update_item.assert_called_with(
        Key={
            'Id': "job123",
            'Sk': "job123",
        },
        UpdateExpression="set #JobStatus = :JobStatus, #JobFinishTime = :JobFinishTime",
        ConditionExpression="#Id = :Id AND #Sk = :Sk AND (#JobStatus = :RUNNING OR #JobStatus = :QUEUED)",
        ExpressionAttributeNames={
            "#Id": "Id",
            "#Sk": "Sk",
            '#JobStatus': 'JobStatus',
            '#JobFinishTime': 'JobFinishTime',
        },
        ExpressionAttributeValues={
            ":Id": "job123",
            ":Sk": "job123",
            ':JobStatus': "FIND_FAILED",
            ':RUNNING': 'RUNNING',
            ':QUEUED': 'QUEUED',
            ':JobFinishTime': 123.0,
        },
        ReturnValues="UPDATED_NEW"
    )
    assert 1 == table.update_item.call_count


@patch("backend.lambdas.jobs.status_updater.determine_status", Mock(return_value="FORGET_FAILED"))
@patch("backend.lambdas.jobs.status_updater.table")
def test_it_handles_forget_failed(table):
    update_status("job123", [{
        "Id": "job123",
        "Sk": "123456",
        "Type": "JobEvent",
        "CreatedAt": 123.0,
        "EventName": "ForgetPhaseFailed",
        "EventData": {}
    }])
    table.update_item.assert_called_with(
        Key={
            'Id': "job123",
            'Sk': "job123",
        },
        UpdateExpression="set #JobStatus = :JobStatus, #JobFinishTime = :JobFinishTime",
        ConditionExpression="#Id = :Id AND #Sk = :Sk AND (#JobStatus = :RUNNING OR #JobStatus = :QUEUED)",
        ExpressionAttributeNames={
            "#Id": "Id",
            "#Sk": "Sk",
            '#JobStatus': 'JobStatus',
            '#JobFinishTime': 'JobFinishTime',
        },
        ExpressionAttributeValues={
            ":Id": "job123",
            ":Sk": "job123",
            ':JobStatus': "FORGET_FAILED",
            ':RUNNING': 'RUNNING',
            ':QUEUED': 'QUEUED',
            ':JobFinishTime': 123.0,
        },
        ReturnValues="UPDATED_NEW"
    )
    assert 1 == table.update_item.call_count


@patch("backend.lambdas.jobs.status_updater.determine_status", Mock(return_value="FAILED"))
@patch("backend.lambdas.jobs.status_updater.table")
def test_it_handles_exception(table):
    update_status("job123", [{
        "Id": "job123",
        "Sk": "123456",
        "Type": "JobEvent",
        "CreatedAt": 123.0,
        "EventName": "Exception",
        "EventData": {}
    }])
    table.update_item.assert_called_with(
        Key={
            'Id': "job123",
            'Sk': "job123",
        },
        UpdateExpression="set #JobStatus = :JobStatus, #JobFinishTime = :JobFinishTime",
        ConditionExpression="#Id = :Id AND #Sk = :Sk AND (#JobStatus = :RUNNING OR #JobStatus = :QUEUED)",
        ExpressionAttributeNames={
            "#Id": "Id",
            "#Sk": "Sk",
            '#JobStatus': 'JobStatus',
            '#JobFinishTime': 'JobFinishTime',
        },
        ExpressionAttributeValues={
            ":Id": "job123",
            ":Sk": "job123",
            ':JobStatus': "FAILED",
            ':RUNNING': 'RUNNING',
            ':QUEUED': 'QUEUED',
            ':JobFinishTime': 123.0,
        },
        ReturnValues="UPDATED_NEW"
    )
    assert 1 == table.update_item.call_count


@patch("backend.lambdas.jobs.status_updater.ddb")
@patch("backend.lambdas.jobs.status_updater.table")
def test_it_handles_already_failed_jobs(table, ddb):
    e = boto3.client("dynamodb").exceptions.ConditionalCheckFailedException
    ddb.meta.client.exceptions.ConditionalCheckFailedException = e
    table.update_item.side_effect = e({}, "ConditionalCheckFailedException")
    update_status("job123", [{
        "Id": "job123",
        "Sk": "123456",
        "Type": "JobEvent",
        "CreatedAt": 123.0,
        "EventName": "Exception",
        "EventData": {}
    }])
    table.update_item.assert_called()


@patch("backend.lambdas.jobs.status_updater.table")
def test_it_throws_for_non_condition_errors(table):
    table.update_item.side_effect = ClientError({"Error": {"Code": "AnError"}}, "update_item")
    with pytest.raises(ClientError):
        update_status("job123", [{
            "Id": "job123",
            "Sk": "123456",
            "Type": "JobEvent",
            "CreatedAt": 123.0,
            "EventName": "Exception",
            "EventData": {}
        }])


@patch("backend.lambdas.jobs.status_updater.table")
def test_it_ignores_none_status_events(table):
    update_status("job123", [{
        "Id": "job123",
        "Sk": "123456",
        "Type": "JobEvent",
        "CreatedAt": 123.0,
        "EventName": "SomeEvent",
        "EventData": {}
    }])
    table.update_item.assert_not_called()