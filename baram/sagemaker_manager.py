import time

import boto3

from baram.log_manager import LogManager


class SagemakerManager(object):
    def __init__(self, domain_id: str = None):
        self.cli = boto3.client('sagemaker')
        self.domain_id = domain_id
        self.logger = LogManager.get_logger('SagemakerManager')

    def list_user_profiles(self,
                           **kwargs):
        response = self.cli.list_user_profiles(DomainIdEquals=self.domain_id,
                                               **kwargs)
        return response['UserProfiles']

    def describe_user_profile(self, user_profile_name):
        response = self.cli.describe_user_profile(DomainId=self.domain_id, UserProfileName=user_profile_name)
        return response

    def list_apps(self,
                  **kwargs):
        response = self.cli.list_apps(DomainIdEquals=self.domain_id,
                                      SortBy='CreationTime',
                                      SortOrder='Descending',
                                      MaxResults=100,
                                      **kwargs)
        return response['Apps']

    def delete_app(self, user_profile_name, app_name, app_type):
        try:
            response = self.cli.delete_app(DomainId=self.domain_id,
                                           UserProfileName=user_profile_name,
                                           AppName=app_name,
                                           AppType=app_type)
            return response
        except:
            return None

    def describe_app(self, user_profile_name, app_name, app_type):
        response = self.cli.describe_app(DomainId=self.domain_id,
                                         UserProfileName=user_profile_name,
                                         AppName=app_name,
                                         AppType=app_type)
        return response

    def create_user_profile(self,
                            user_profile_name: str,
                            execution_role: str,
                            **kwargs):
        print(f'start creating {user_profile_name}')
        response = self.cli.create_user_profile(DomainId=self.domain_id,
                                                UserProfileName=user_profile_name,
                                                UserSettings={
                                                    'ExecutionRole': execution_role},
                                                **kwargs)
        return response

    def delete_user_profile(self, user_profile_name):
        try:
            self.describe_user_profile(user_profile_name)
        except self.cli.exceptions.ResourceNotFound:
            self.logger.info(f'user {user_profile_name} does not exist.')
            return

        self.logger.info(f'list apps from {user_profile_name}')
        apps = self.list_apps(UserProfileNameEquals=user_profile_name)
        for app in apps:
            try:
                response = self.describe_app(user_profile_name, app['AppName'], app['AppType'])
                if response['Status'] != 'Deleted' and response['Status'] != 'Deleting':
                    self.delete_app(user_profile_name, app['AppName'], app['AppType'])
            except self.cli.exceptions.ResourceNotFound:
                pass
            except self.cli.exceptions.ResourceInUse as e:
                self.logger.info(e)
                return
        self.logger.info(f'deleting {len(apps)} apps.')
        delete_cnt = 0
        elapsed_secs = 0
        while delete_cnt < len(apps):
            delete_cnt = 0
            for app in apps:
                response = self.describe_app(user_profile_name, app['AppName'], app['AppType'])
                self.logger.info(f'status = {response["Status"]}')
                if response['Status'] == 'Deleted' or response['Status'] == 'Failed':
                    delete_cnt += 1
            time.sleep(5)
            elapsed_secs += 5
            self.logger.info(f'wait 5 seconds. delete_cnt={delete_cnt}, elapsed_secs={elapsed_secs}')
        return self.cli.delete_user_profile(DomainId=self.domain_id, UserProfileName=user_profile_name)

    def list_domains(self):
        return self.cli.list_domains()['Domains']

    def delete_domain(self):
        response = self.cli.delete_domain(DomainId=self.domain_id, RetentionPolicy={'HomeEfsFileSystem': 'Delete'})
        return response

    def create_domain(self,
                      domain_name: str,
                      execution_role_name: str,
                      sg_group: str,
                      s3_kms_id: str,
                      efs_kms_id: str,
                      s3_output_path: str,
                      vpc_id: str,
                      subnet_id1: str,
                      subnet_id2: str,
                      instance_type: str = 'ml.t3.micro'):
        pass
        # TODO: TBD.
        response = self.cli.create_domain(
            DomainName=domain_name,
            AuthMode='IAM',
            DefaultUserSettings={
                'ExecutionRole': execution_role_name,
                'SecurityGroups': [
                    sg_group,
                ],
                'SharingSettings': {
                    'NotebookOutputOption': 'Allowed',
                    'S3OutputPath': s3_output_path,
                    'S3KmsKeyId': s3_kms_id
                },
                'JupyterServerAppSettings': {
                    'DefaultResourceSpec': {
                        'SageMakerImageArn': 'string',
                        'SageMakerImageVersionArn': 'string',
                        'InstanceType': instance_type
                    }
                },
                'KernelGatewayAppSettings': {
                    'DefaultResourceSpec': {
                        'SageMakerImageArn': 'string',
                        'SageMakerImageVersionArn': 'string',
                        'InstanceType': instance_type
                    },
                    'CustomImages': [
                        {
                            'ImageName': 'string',
                            'ImageVersionNumber': 1,
                            'AppImageConfigName': 'string'
                        },
                    ],
                    'LifecycleConfigArns': [
                        'string',
                    ]
                }
            },
            SubnetIds=[
                'string',
            ],
            VpcId=vpc_id,
            Tags=[
                {
                    'Key': 'string',
                    'Value': 'string'
                },
            ],
            AppNetworkAccessType='VpcOnly',
            KmsKeyId=efs_kms_id,
            AppSecurityGroupManagement='Service' | 'Customer',
            DomainSettings={
                'SecurityGroupIds': [
                    'string',
                ]
            }
        )

    def describe_image(self, image_name):
        try:
            return self.cli.describe_image(ImageName=image_name)
        except self.cli.exceptions.ResourceNotFound:
            self.logger.info('ResourceNotFound')
            return None

    def describe_image_version(self, image_name):
        try:
            return self.cli.describe_image_version(ImageName=image_name)
        except self.cli.exceptions.ResourceNotFound:
            self.logger.info('ResourceNotFound')
            return None

    def create_image_version(self, image_uri: str, name: str):
        return self.cli.create_image_version(
            BaseImage=image_uri,
            ImageName=name
        )

    def delete_image(self, image_name):
        try:
            return self.cli.delete_image(ImageName=image_name)
        except self.cli.exceptions.ResourceNotFound:
            self.logger.info('ResourceNotFound')
            return None

    def delete_image_version(self, image_name, version):
        try:
            return self.cli.delete_image_version(ImageName=image_name, Version=version)
        except self.cli.exceptions.ResourceNotFound:
            self.logger.info('ResourceNotFound')
            return None

    def recreate_all_user_profiles(self):
        user_profiles = [self.describe_user_profile(user_profile_name=x['UserProfileName'])
                         for x in self.list_user_profiles()]
        print(f"user profiles to recreate: {[x['UserProfileName'] for x in user_profiles]}")

        for i in user_profiles:
            print(f"start deleting {i['UserProfileName']}")
            self.delete_user_profile(user_profile_name=i['UserProfileName'])
            while i['UserProfileName'] in self.list_user_profiles():
                time.sleep(5)
            else:
                print(f"{i['UserProfileName']} deleted")
                time.sleep(5)
            self.create_user_profile(user_profile_name=i['UserProfileName'],
                                     execution_role=i['UserSettings']['ExecutionRole'])
            print(f"{i['UserProfileName']} created")
