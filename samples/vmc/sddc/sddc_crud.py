#!/usr/bin/env python

"""
* *******************************************************
* Copyright (c) VMware, Inc. 2017. All Rights Reserved.
* SPDX-License-Identifier: MIT
* *******************************************************
*
* DISCLAIMER. THIS PROGRAM IS PROVIDED TO YOU "AS IS" WITHOUT
* WARRANTIES OR CONDITIONS OF ANY KIND, WHETHER ORAL OR WRITTEN,
* EXPRESS OR IMPLIED. THE AUTHOR SPECIFICALLY DISCLAIMS ANY IMPLIED
* WARRANTIES OR CONDITIONS OF MERCHANTABILITY, SATISFACTORY QUALITY,
* NON-INFRINGEMENT AND FITNESS FOR A PARTICULAR PURPOSE.
"""

__author__ = 'VMware, Inc.'

import argparse
import atexit
import os
import requests
from random import randrange
from tabulate import tabulate

from com.vmware.vmc.model_client import AwsSddcConfig, ErrorResponse
from com.vmware.vapi.std.errors_client import InvalidRequest
from vmware.vapi.vmc.client import create_vmc_client

from samples.vmc.helpers.vmc_task_helper import wait_for_task


class CreateDeleteSDDC(object):
    """
    Demonstrates create and delete a SDDC

    Sample Prerequisites:
        - An organization associated with the calling user.
    """

    def __init__(self):
        self.org_id = None
        self.vmc_client = None
        self.sddc_id = None
        self.sddc_name = None
        self.listsddc = None
        self.createsddc = None
        self.deletesddc = None
        self.cleanup = None
        self.refresh_token = None
        self.interval_sec = None

    def option(self):
        parser = argparse.ArgumentParser()

        parser.add_argument('-r', '--refresh-token',
                            required=True,
                            help='VMware Cloud API refresh token')

        parser.add_argument('-o', '--org-id',
                            required=True,
                            help='Organization identifier.')

        parser.add_argument('-sn', '--sddc-name',
                            help="Name of the SDDC to be created. "
                                 "Default is 'Sample SDDC xx'")

        parser.add_argument('-i', '--interval-sec',
                            default=60,
                            help='Task pulling interval in sec')

        parser.add_argument('-ls', '--listsddc',
                            action='store_true',
                            help='List SDDCs in the specified Org')

        parser.add_argument('-cs', '--createsddc',
                            action='store_true',
                            help='Create an SDDC in the specified Org')

        parser.add_argument('-ds', '--deletesddc',
                            action='store_true',
                            help='Deletes the SDDC in the specified Org ')                                                        

        parser.add_argument('-c', '--cleardata',
                            action='store_true',
                            help='Clean up after sample run')

        args = parser.parse_args()

        self.refresh_token = args.refresh_token
        self.org_id = args.org_id
        self.listsddc = args.listsddc
        self.createsddc = args.createsddc
        self.deletesddc = args.deletesddc
        self.cleanup = args.cleardata

        self.sddc_name = args.sddc_name or \
                         'Sample SDDC {}'.format(randrange(100))
        self.interval_sec = int(args.interval_sec)

    def setup(self):

        # Login to VMware Cloud on AWS
        session = requests.Session()
        self.vmc_client = create_vmc_client(self.refresh_token, session)
        atexit.register(session.close)

        # Check if the organization exists
        orgs = self.vmc_client.Orgs.list()
        if self.org_id not in [org.id for org in orgs]:
            raise ValueError("Org with ID {} doesn't exist".format(self.org_id))

    def create_sddc(self):
        print('\n# Example: Create a SDDC ({}) in org {}:'.
              format(self.sddc_name, self.org_id))

        provider = os.environ.get('VMC_PROVIDER', 'AWS')
        sddc_config = AwsSddcConfig(
            region='US_WEST_2', num_hosts=1, name=self.sddc_name,
            provider=provider)

        try:
            task = self.vmc_client.orgs.Sddcs.create(org=self.org_id,
                                                     sddc_config=sddc_config)
        except InvalidRequest as e:
            # Convert InvalidRequest to ErrorResponse to get error message
            error_response = e.data.convert_to(ErrorResponse)
            raise Exception(error_response.error_messages)

        wait_for_task(task_client=self.vmc_client.orgs.Tasks,
                      org_id=self.org_id,
                      task_id=task.id,
                      interval_sec=self.interval_sec)

        print('\n# Example: SDDC created:')
        self.sddc_id = task.resource_id
        sddc = self.vmc_client.orgs.Sddcs.get(self.org_id, self.sddc_id)
        self.print_output([sddc])

    def delete_sddc(self):
        print('\n# Example: Delete SDDC {} from org {}'.format(self.sddc_id,
                                                                self.org_id))

        try:
            task = self.vmc_client.orgs.Sddcs.delete(org=self.org_id,
                                                     sddc=self.sddc_id)
        except InvalidRequest as e:
            # Convert InvalidRequest to ErrorResponse to get error message
            error_response = e.data.convert_to(ErrorResponse)
            raise Exception(error_response.error_messages)

        wait_for_task(task_client=self.vmc_client.orgs.Tasks,
                      org_id=self.org_id,
                      task_id=task.id,
                      interval_sec=self.interval_sec)

        print('\n# Example: Remaining SDDCs:'.
              format(self.org_id))
        sddcs = self.vmc_client.orgs.Sddcs.list(self.org_id)
        self.print_output(sddcs)

    def list_sddc(self):
        sddcs = self.vmc_client.orgs.Sddcs.list(self.org_id)
        if not sddcs:
            raise ValueError('The sample requires at least one SDDC associated'
                             'with the calling user')
        print("\n# Example: List SDDCs")
        self.print_output(sddcs)

    def print_output(self, sddcs):
        table = []
        for sddc in sddcs:
            table.append([sddc.id, sddc.name, sddc.resource_config.region])
        print(tabulate(table, ['ID', 'Name', 'AWS Region']))        

def main():
    sddc_operations = CreateDeleteSDDC()
    sddc_operations.option()
    sddc_operations.setup()
    if sddc_operations.listsddc:
        sddc_operations.list_sddc()
    if sddc_operations.createsddc:
        sddc_operations.create_sddc()
    if sddc_operations.deletesddc:
        sddc_operations.delete_sddc()
    if sddc_operations.cleanup:
        sddc_operations.delete_sddc()


if __name__ == '__main__':
    main()