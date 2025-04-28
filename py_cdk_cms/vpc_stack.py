from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
import aws_cdk as cdk

from constructs import Construct


class VPCStack(Stack):
    """
    VPC Stack for the CMS application.
    This stack creates a VPC with public and private subnets.
    Public subnets are used for load balancers and NAT gateways,
    while private subnets are used for ECS tasks and RDS instances.
    """

    vpc: ec2.Vpc

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "cms_vpc",
            vpc_name="cms_vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="ingress",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="private_egress",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        self.vpc_output = cdk.CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name="VPC-ID",
        )
