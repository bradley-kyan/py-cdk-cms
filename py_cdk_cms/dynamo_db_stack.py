from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    Stack,
)

from constructs import Construct
import aws_cdk as cdk
import os
import logging

logger = logging.getLogger(__name__)

class DynamoDBStack(Stack):
    """
    DynamoDB Stack for the CMS application.
    """
    
    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)
        
        self.create_dynamodb_table("cms-table")
        

    def create_dynamodb_table(self, table_name: str) -> dynamodb.TableV2:
        """
        Create a DynamoDB table.
        """
        
        enviornment = os.environ.get("ENVIRONMENT")
        
        if enviornment == "dev":
            logger.info("Creating DynamoDB table in development environment")
            table_name = f"{table_name}_dev"
            deletion_protection = False
        elif enviornment == "prod":
            logger.info("Creating DynamoDB table in production environment")
            table_name = f"{table_name}_prod"
            deletion_protection = True
        
        table = dynamodb.TableV2(
            self,
            table_name,
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="pk",
                type=dynamodb.AttributeType.STRING
            ),
            deletion_protection=deletion_protection,
            table_class=dynamodb.TableClass.STANDARD_INFREQUENT_ACCESS,
            encryption=dynamodb.TableEncryptionV2.dynamo_owned_key(),
            billing=dynamodb.Billing.on_demand(),
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        return table