import aws_cdk as core
import aws_cdk.assertions as assertions

from py_cdk_cms.py_cdk_cms_stack import PyCdkCmsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in py_cdk_cms/py_cdk_cms_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = PyCdkCmsStack(app, "py-cdk-cms")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
