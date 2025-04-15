from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
)
from constructs import Construct
import aws_cdk as cdk
import os
import logging
import boto3

logger = logging.getLogger(__name__)


class ECSStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        ecr_repository: ecr.Repository,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create ECS Cluster
        cluster = ecs.Cluster(self, "CMSCluster", vpc=vpc)

        # Security Group for the Fargate
        fargate_service_sg = ec2.SecurityGroup(
            self,
            "FargateServiceSG",
            vpc=vpc,
            description="Security group for Fargate service",
            allow_all_outbound=True,
        )

        # Create Security Group for ALB
        alb_security_group = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=vpc,
            description="Security group for Application Load Balancer",
            allow_all_outbound=True,
        )

        # Allow inbound traffic to ALB
        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic from internet",
        )

        # Allow ALB to communicate with Fargate service
        fargate_service_sg.add_ingress_rule(
            peer=alb_security_group,
            connection=ec2.Port.tcp(80),
            description="Allow traffic from ALB",
        )

        # Add HTTPS traffic if needed
        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS traffic from internet",
        )

        # Try get the image from ECR
        if not self.container_image_exists(ecr_repository):
            logger.info("Image not found in ECR. Not creating a new contianer")
            return None

        container_image = ecs.ContainerImage.from_ecr_repository(
            ecr_repository, "latest"
        )

        # Create Fargate Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "CMSTaskDef",
            memory_limit_mib=1024,
            cpu=256,
        )

        # Grant ecs permissions to pull images from ECR
        ecr_repository.grant_pull(task_definition.task_role)

        # Add container to task def
        container = task_definition.add_container(
            "CMSContainer",
            image=container_image,
            logging=ecs.LogDrivers.aws_logs(stream_prefix="cms-container"),
            environment={"ENVIRONMENT": f"{os.environ.get('ENVIRONMENT')}"},
        )

        # Add port mapping
        container.add_port_mappings(ecs.PortMapping(container_port=80))

        # Create ALB
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "ServiceALB",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group,
        )

        # Create Fargate Service
        fargate_service = ecs.FargateService(
            self,
            "CMSService",
            cluster=cluster,
            task_definition=task_definition,
            security_groups=[fargate_service_sg],
            desired_count=2,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
            ),
            assign_public_ip=False,
        )

        # Create ALB Target Group
        target_group = elbv2.ApplicationTargetGroup(
            self,
            "ServiceTargetGroup",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            # Health check needs to be implemented with the cms
            # health_check=elbv2.HealthCheck(
            #     path="/health",
            #     healthy_http_codes="200-299",
            #     interval=cdk.Duration.seconds(60),
            #     timeout=cdk.Duration.seconds(5)
            # )
        )

        # Add listener to ALB
        alb.add_listener(
            "Listener", port=80, default_target_groups=[target_group]
        )

        # Associate Fargate Service with Target Group
        fargate_service.attach_to_application_target_group(target_group)

        # Add auto-scaling
        scaling = fargate_service.auto_scale_task_count(max_capacity=3, min_capacity=1)

        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=cdk.Duration.seconds(60),
            scale_out_cooldown=cdk.Duration.seconds(60),
        )

        # Optional: Add scaling based on memory utilization
        scaling.scale_on_memory_utilization(
            "MemoryScaling",
            target_utilization_percent=70,
            scale_in_cooldown=cdk.Duration.seconds(60),
            scale_out_cooldown=cdk.Duration.seconds(60),
        )

        # Add CloudFormation outputs
        CfnOutput(
            self,
            "LoadBalancerDNS",
            value=alb.load_balancer_dns_name,
            description="Load balancer DNS name",
        )

        CfnOutput(
            self,
            "ServiceSecurityGroupId",
            value=fargate_service_sg.security_group_id,
            description="Security group ID for the Fargate service",
        )

        CfnOutput(
            self,
            "AlbSecurityGroupId",
            value=alb_security_group.security_group_id,
            description="Security group ID for the ALB",
        )

        logger.info("ECS Stack deployed successfully")

    def container_image_exists(self, ecr_repository: ecr.Repository) -> bool:
        """
        Check if the container image exists in ECR.
        """
        try:
            client = boto3.client("ecr")
            response = client.describe_images(
                repositoryName=ecr_repository.repository_name,
                imageIds=[{"imageTag": "latest"}],
            )
            return len(response["imageDetails"]) > 0
        except Exception as e:
            logger.error(f"Error checking image in ECR: {e}")
            return False
