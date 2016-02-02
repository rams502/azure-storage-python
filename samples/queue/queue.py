﻿# coding: utf-8

#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import time
import uuid
from datetime import datetime, timedelta
from azure.storage import (
    AccessPolicy,
    ResourceTypes,
    AccountPermissions,
    CloudStorageAccount,
    Logging,
    Metrics,
    CorsRule,
)
from azure.storage.queue import (
    QueueService,
    QueuePermissions,
    QueueMessageFormat,
)
from azure.common import (
    AzureConflictHttpError,
    AzureMissingResourceHttpError,
)

ACCOUNT_NAME = ''
ACCOUNT_KEY = ''
account = CloudStorageAccount(ACCOUNT_NAME, ACCOUNT_KEY)

class QueueSamples():  

    def run_all_samples(self):
        self.create_queue()
        self.delete_queue()
        self.exists()
        self.list_queues()
        self.metadata()        
        self.put_message()
        self.get_messages()
        self.peek_messages()
        self.clear_messages()
        self.delete_message()
        self.update_message()
        self.alternative_encoding()
        self.queue_sas()
        self.account_sas()

        # The below run more slowly as they have sleeps
        self.queue_acl()
        self.sas_with_signed_identifiers()
        self.service_properties()

    def _get_queue_reference(self, prefix='queue'):
        queue_name = '{}{}'.format(prefix, str(uuid.uuid4()).replace('-', ''))
        return queue_name

    def _create_queue(self, service, prefix='queue'):
        queue_name = self._get_queue_reference(prefix)
        service.create_queue(queue_name)
        return queue_name

    def create_queue(self):
        service = account.create_queue_service()

        # Basic
        queue_name1 = self._get_queue_reference()
        created = service.create_queue(queue_name1) # True

        # Metadata
        metadata = {'val1': 'foo', 'val2': 'blah'}
        queue_name2 = self._get_queue_reference()
        created = service.create_queue(queue_name2, metadata=metadata) # True

        # Fail on exist
        queue_name3 = self._get_queue_reference()
        created = service.create_queue(queue_name3) # True 
        created = service.create_queue(queue_name3) # False
        try:
            service.create_queue(queue_name3, fail_on_exist=True)
        except AzureConflictHttpError:
            pass

        service.delete_queue(queue_name1)
        service.delete_queue(queue_name2)
        service.delete_queue(queue_name3)

    def delete_queue(self):
        service = account.create_queue_service()

        # Basic
        queue_name = self._create_queue(service)
        deleted = service.delete_queue(queue_name) # True 

        # Fail not exist
        queue_name = self._get_queue_reference()
        deleted = service.delete_queue(queue_name) # False
        try:
            service.delete_queue(queue_name, fail_not_exist=True)
        except AzureMissingResourceHttpError:
            pass

    def exists(self):
        service = account.create_queue_service()
        queue_name = self._get_queue_reference()

        # Does not exist
        exists = service.exists(queue_name) # False

        # Exists
        service.create_queue(queue_name)
        exists = service.exists(queue_name) # True

        service.delete_queue(queue_name)

    def list_queues(self):
        service = account.create_queue_service()
        queue_name1 = self._get_queue_reference()
        service.create_queue('queue1', metadata={'val1': 'foo', 'val2': 'blah'})

        queue_name2 = self._create_queue(service, 'queue2')
        queue_name3 = self._create_queue(service, 'thirdq')

        # Basic
        # Commented out as this will list every queue in your account
        # queues = list(service.list_queues())
        # for queue in queues:
        #    print(queue.name) # queue1, queue2, thirdq, all other queues created in the service        

        # Prefix
        queues = list(service.list_queues(prefix='queue'))
        for queue in queues:
            print(queue.name) # queue1, queue2

        # Metadata
        queues = list(service.list_queues(prefix='queue', include_metadata=True))
        queue = next((q for q in queues if q.name == 'queue1'), None)
        metadata = queue.metadata # {'val1': 'foo', 'val2': 'blah'}

        service.delete_queue(queue_name1)
        service.delete_queue(queue_name2)
        service.delete_queue(queue_name3)

    def metadata(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)
        metadata = {'val1': 'foo', 'val2': 'blah'}

        # Basic
        service.set_queue_metadata(queue_name, metadata=metadata)
        metadata = service.get_queue_metadata(queue_name) # metadata={'val1': 'foo', 'val2': 'blah'}

        approximate_message_count = metadata.approximate_message_count # approximate_message_count = 0       

        # Replaces values, does not merge
        metadata = {'new': 'val'}
        service.set_queue_metadata(queue_name, metadata=metadata)
        metadata = service.get_queue_metadata(queue_name) # metadata={'new': 'val'}

        # Capital letters
        metadata = {'NEW': 'VAL'}
        service.set_queue_metadata(queue_name, metadata=metadata)
        metadata = service.get_queue_metadata(queue_name) # metadata={'new': 'VAL'}

        # Clearing
        service.set_queue_metadata(queue_name)
        metadata = service.get_queue_metadata(queue_name) # metadata={}
    
        service.delete_queue(queue_name)
    
    def put_message(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)

        # Basic
        # immediately visibile and expires in 7 days
        service.put_message(queue_name, 'message1')

        # Visbility timeout
        # visible in 5 seconds and expires in 7 days
        service.put_message(queue_name, 'message2', visibility_timeout=5)

        # Time to live
        # immediately visibile and expires in 60 seconds
        service.put_message(queue_name, 'message3', time_to_live=60)

        service.delete_queue(queue_name)
    
    def get_messages(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)
        service.put_message(queue_name, 'message1')
        service.put_message(queue_name, 'message2')
        service.put_message(queue_name, 'message3')
        service.put_message(queue_name, 'message4')

        # Azure queues are not strictly ordered so the below messages returned are estimates
        # Ex: We may return message2 for the first sample and then message1 and message3 for the second

        # Basic, only gets 1 message
        messages = service.get_messages(queue_name)
        for message in messages:
            print(message.content) # message1

        # Num messages
        messages = service.get_messages(queue_name, num_messages=2)
        for message in messages:
            print(message.content) # message2, message3
        
        # Visibility
        messages = service.get_messages(queue_name, visibility_timeout=10)
        for message in messages:
            print(message.content) # message4
        # message4 has a visibility timeout of only 10 seconds rather than 30

        service.delete_queue(queue_name)
    
    def peek_messages(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)
        service.put_message(queue_name, 'message1')
        service.put_message(queue_name, 'message2')

        # Azure queues are not strictly ordered so the below messages returned are estimates
        # Ex: We may return message2 for the first sample and then message1 and message2 for the second

        # Basic
        # does not change the visibility timeout
        # does not return pop_receipt, or time_next_visible
        messages = service.peek_messages(queue_name)
        for message in messages:
            print(message.content) # message1

        # Num messages
        messages = service.get_messages(queue_name, num_messages=2)
        for message in messages:
            print(message.content) # message1, message2

        service.delete_queue(queue_name)
    
    def clear_messages(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)
        service.put_message(queue_name, 'message1')
        service.put_message(queue_name, 'message2')

        # Basic
        service.clear_messages(queue_name)
        messages = service.peek_messages(queue_name) # messages = {}

        service.delete_queue(queue_name)
    
    def delete_message(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)
        service.put_message(queue_name, 'message1')
        service.put_message(queue_name, 'message2')
        messages = service.get_messages(queue_name)

        # Basic
        # Deleting requires the message id and pop receipt (returned by get_messages)
        service.delete_message(queue_name, messages[0].id, messages[0].pop_receipt)      

        messages = service.peek_messages(queue_name)
        for message in messages:
            print(message.content) # either message1 or message 2

        service.delete_queue(queue_name)
    
    def update_message(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)
        service.put_message(queue_name, 'message1')
        messages = service.get_messages(queue_name)

        # Basic
        # Must update visibility timeout, but can use 0
        # updates the visibility timeout and returns pop_receipt and time_next_visible
        message = service.update_message(queue_name,
                               messages[0].id,
                               messages[0].pop_receipt,
                               0)               

        # With Content
        # Use pop_receipt from previous update
        # message will appear in 30 seconds with the new content
        message = service.update_message(queue_name,
                               messages[0].id,
                               message.pop_receipt,
                               30,
                               content='new text')       

        service.delete_queue(queue_name)

    def alternative_encoding(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)

        # set encoding/decoding to base64 with byte strings
        # default encoding is xml encoded/decoded unicode strings
        # base64 encoding is used in some other storage libraries, use for compatibility
        service.encode_function = QueueMessageFormat.binary_base64encode
        service.decode_function = QueueMessageFormat.binary_base64decode

        content = b'bytedata'
        service.put_message(queue_name, content)

        messages = service.peek_messages(queue_name)
        for message in messages:
            print(message.content) # b'bytedata'

        service.delete_queue(queue_name)

    def queue_sas(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)
        service.put_message(queue_name, 'message1')

        # Access only to the messages in the given queue
        # Process permissions to access messages
        # Expires in an hour
        token = service.generate_queue_shared_access_signature(
            queue_name,
            QueuePermissions.PROCESS,
            datetime.utcnow() + timedelta(hours=1),
        )

        # Create a service and use the SAS
        sas_service = QueueService(
            account_name=ACCOUNT_NAME,
            sas_token=token,
        )

        messages = sas_service.get_messages(queue_name)
        for message in messages:
            print(message.content) # message1

        service.delete_queue(queue_name)

    def account_sas(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)
        metadata = {'val1': 'foo', 'val2': 'blah'}
        service.set_queue_metadata(queue_name, metadata=metadata)

        # Access to all messages in the queues and the queues themselves
        # Read permissions to access messages and the queue
        # Expires in an hour
        token = service.generate_account_shared_access_signature(
            ResourceTypes.CONTAINER,
            AccountPermissions.READ,
            datetime.utcnow() + timedelta(hours=1),
        )

        # Create a service and use the SAS
        sas_service = QueueService(
            account_name=ACCOUNT_NAME,
            sas_token=token,
        )
        metadata = sas_service.get_queue_metadata(queue_name) # metadata={'val1': 'foo', 'val2': 'blah'}

        service.delete_queue(queue_name)

    def queue_acl(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)

        # Basic
        access_policy = AccessPolicy(permission=QueuePermissions.READ,
                                     expiry=datetime.utcnow() + timedelta(hours=1))
        identifiers = {'id': access_policy}
        service.set_queue_acl(queue_name, identifiers)

        # Wait 30 seconds for acl to propagate
        time.sleep(30)
        acl = service.get_queue_acl(queue_name) # {id: AccessPolicy()}

        # Replaces values, does not merge
        access_policy = AccessPolicy(permission=QueuePermissions.READ,
                                     expiry=datetime.utcnow() + timedelta(hours=1))
        identifiers = {'id2': access_policy}
        service.set_queue_acl(queue_name, identifiers)

        # Wait 30 seconds for acl to propagate
        time.sleep(30)
        acl = service.get_queue_acl(queue_name) # {id2: AccessPolicy()}

        # Clear
        service.set_queue_acl(queue_name)

        # Wait 30 seconds for acl to propagate
        time.sleep(30)
        acl = service.get_queue_acl(queue_name) # {}

        service.delete_queue(queue_name)

    def sas_with_signed_identifiers(self):
        service = account.create_queue_service()
        queue_name = self._create_queue(service)
        service.put_message(queue_name, 'message1')

        # Set access policy on queue
        access_policy = AccessPolicy(permission=QueuePermissions.PROCESS,
                                     expiry=datetime.utcnow() + timedelta(hours=1))
        identifiers = {'id': access_policy}
        acl = service.set_queue_acl(queue_name, identifiers)

        # Wait 30 seconds for acl to propagate
        time.sleep(30)

        # Indicates to use the access policy set on the queue
        token = service.generate_queue_shared_access_signature(
            queue_name,
            id='id'
        )

        # Create a service and use the SAS
        sas_service = QueueService(
            account_name=ACCOUNT_NAME,
            sas_token=token,
        )

        messages = sas_service.get_messages(queue_name)
        for message in messages:
            print(message.content) # message1

        service.delete_queue(queue_name)

    def service_properties(self):
        service = account.create_queue_service()

        # Basic
        service.set_queue_service_properties(logging=Logging(delete=True), 
                                             hour_metrics=Metrics(enabled=True, include_apis=True), 
                                             minute_metrics=Metrics(enabled=True, include_apis=False), 
                                             cors=[CorsRule(allowed_origins=['*'], allowed_methods=['GET'])])

        # Wait 30 seconds for settings to propagate
        time.sleep(30)

        props = service.get_queue_service_properties() # props = ServiceProperties() w/ all properties specified above

        # Omitted properties will not overwrite what's already on the service
        # Empty properties will clear
        service.set_queue_service_properties(cors=[])

        # Wait 30 seconds for settings to propagate
        time.sleep(30)

        props = service.get_queue_service_properties() # props = ServiceProperties() w/ CORS rules cleared
