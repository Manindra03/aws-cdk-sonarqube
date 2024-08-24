#!/usr/bin/env python3

from aws_cdk import App
import os
from dotenv import load_dotenv
from aws_cdk_sonarqube.aws_cdk_sonarqube_stack import SonarqubeStack
from aws_cdk_sonarqube.vpc_stack import VpcStack

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

app = App()

aws_environment = {
    "account": os.environ.get("CDK_DEFAULT_ACCOUNT"),
    "region": os.environ.get("CDK_DEFAULT_REGION")
}

vpc_stack = VpcStack(
    app,
    "VPC-stack",
    env=aws_environment,
    stack_name="vpcstack",
    description="VPC Network stack for SonarQube"
)

sonarqube_stack = SonarqubeStack(
    app,
    "Sonarqube-stack",
    env=aws_environment,
    stack_name="sonarqubestack",
    description="SonarQube stack"
)

sonarqube_stack.add_dependency(vpc_stack)

app.synth()