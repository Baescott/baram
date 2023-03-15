import boto3
import traceback

from baram.log_manager import LogManager


class EC2Manager(object):
    def __init__(self):
        self.cli = boto3.client('ec2')
        self.logger = LogManager().get_logger()

    def list_security_groups(self):
        """
        Describes the specified security groups or all of your security groups.

        :return: SecurityGroups
        """
        return self.cli.describe_security_groups()['SecurityGroups']

    def list_instances_with_status(self, status: str = 'running'):
        """
        Describes all instances in specific status (ex: 'running', ...)

        :return: Instances, with status
        """
        try:
            instances = [instance['Instances'][0] for instance in self.describe_instances()['Reservations']]
            return [instance for instance in instances if instance['State']['Name'] == status]
        except:
            print(traceback.format_exc())

    def delete_unused_key_pairs(self):
        """
        Delete redundant key pairs (i.e. not related to any instances)
        """
        key_pairs_redundant = self.list_unused_key_pairs()
        try:
            for key_pair in key_pairs_redundant:
                self.cli.delete_key_pair(KeyName=key_pair)
                self.logger.info('key pair has deleted')
        except:
            print(traceback.format_exc())

    def list_unused_key_pairs(self):
        """
        Describes all disused key pairs

        :return: KeyName
        """
        key_pairs_total = self.list_key_pairs()
        instances = [instance['Instances'][0] for instance in self.describe_instances()['Reservations']]
        key_pairs_using = [instance['KeyName'] for instance in instances]

        return key_pairs_total - set(key_pairs_using)

    def list_key_pairs(self):
        """
        Describes all key pairs

        :return: KeyName
        """
        key_pairs = self.cli.describe_key_pairs()['KeyPairs']
        return set([key_pair['KeyName'] for key_pair in key_pairs])

    def list_vpcs(self):
        """
        List one or more of your VPCs.

        :return: Vpcs
        """
        return self.cli.describe_vpcs()['Vpcs']

    def list_subnet(self):
        """
        List one or more of your Subnets.

        :return: Subnets
        """
        return self.cli.describe_subnets()['Subnets']

    def get_sg_id(self, group_name: str):
        """
        Retrieve subnet id from group name.

        :param group_name: group name
        :return: subnet id
        """
        return next(
            (i['GroupId'] for i in self.list_security_groups()
             if group_name.lower() in i['GroupName'].lower()), None)

    def get_vpc_id(self, vpc_name: str):
        """
        Retrieve vpc id from vpc name.

        :param vpc_name: vpc name
        :return: VpcId
        """
        return next(i['VpcId'] for i in self.list_vpcs() if 'Tags' in i
                    for t in i['Tags'] if vpc_name.lower() in t['Value'].lower())

    def get_subnet_id(self, vpc_id: str, subnet_name: str):
        """
        Retrieve subnet id from vpc id and subnet name.

        :param vpc_id: vpc_id
        :param subnet_name: subnet_name
        :return: SubnetId
        """
        return next(s['SubnetId'] for s in self.list_subnet() if vpc_id == s['VpcId'] and 'Tags' in s
                    for t in s['Tags'] if subnet_name == t['Value'])

    def get_ec2_id(self, name):
        """

        :param name: ec2 instance name
        :return:
        """
        ec2 = boto3.resource('ec2')
        return next(
            i.id for i in ec2.instances.all() if i.state['Name'] == 'running' for t in i.tags if name == t['Value'])

    def describe_instances(self, instance_id_list: list = None):
        """

        Retrieve ec2 instance description.
        :param instance_id_list: the list of InstanceIds
        :return:
        """
        if instance_id_list is not None:
            return self.cli.describe_instances(InstanceIds=instance_id_list)
        else:
            return self.cli.describe_instances()

    def get_ec2_instances_with_imds_v1(self):
        """

        :return: get ec2 instances that support imds_v1.
        """
        response = self.describe_instances()
        return [i['InstanceId'] for r in response['Reservations']
                for i in r['Instances']
                if i['MetadataOptions']['HttpTokens'] != 'required' and i['State']['Name'] == 'running']

    def apply_imdsv2_only_mode(self,
                               instances_list: list = None,
                               http_put_response_hop_limit: int = 1):
        """

        Apply imdsv2 only mode into ec2 instances.
        :param instances_list:
        :param http_put_response_hop_limit: see https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_InstanceMetadataOptionsRequest.html.
        :return:
        """
        for i in instances_list:
            self.cli.modify_instance_metadata_options(InstanceId=i,
                                                      HttpTokens='required',
                                                      HttpPutResponseHopLimit=http_put_response_hop_limit,
                                                      HttpEndpoint='enabled')
