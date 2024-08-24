from aws_cdk import Stack, aws_ec2 as ec2
from constructs import Construct

class VpcStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Creating a VPC with 1 AZ and 1 Public Subnet
        ec2.Vpc(self, "vpc",
            vpc_name="sonar-vpc",
            max_azs=1,
            subnet_configuration=[ec2.SubnetConfiguration(
                cidr_mask=24,
                name="public-subnet",
                subnet_type=ec2.SubnetType.PUBLIC
            )]
        )