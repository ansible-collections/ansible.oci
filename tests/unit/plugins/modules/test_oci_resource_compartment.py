from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pytest

from ansible_collections.ansible.oci.plugins.modules import oci_resource_compartment as m


class Result(Exception):
    def __init__(self, **data):
        self.data = data


def raise_result(**data):
    raise Result(**data)


@pytest.fixture
def client_factory():
    with patch.object(m, 'create_service_client') as factory:
        yield factory


@pytest.fixture
def work_client():
    work = Mock()
    work.base_client.timeout = (10, 60)
    work.list_work_request_errors.__name__ = 'list_resources'
    work.list_work_request_errors.return_value = m.oci.response.Response(200, {}, [], None)
    work.get_work_request.return_value = work_response()
    return work


@pytest.fixture
def mover(client_factory, work_client):
    module = Mock()
    module.params = dict(resource_id='ocid1.instance.oc1.region.example', target_compartment_id='ocid1.compartment.oc1..target',
                         wait=True, wait_timeout=30, wait_interval=1, region='resource-region')
    module.check_mode = False
    module.exit_json.side_effect = raise_result
    module.fail_json.side_effect = lambda **data: raise_result(failed=True, **data)
    identity, search = Mock(), Mock()
    for fn in (identity.list_region_subscriptions, identity.list_bulk_action_resource_types, search.search_resources):
        fn.__name__ = 'list_resources'
    search.base_client.timeout = (10, 60)
    identity.base_client.config = {'tenancy': 'ocid1.tenancy.oc1..target'}
    identity.list_region_subscriptions.return_value = m.oci.response.Response(200, {}, [NS(region_name='home', is_home_region=True)], None)
    identity.list_bulk_action_resource_types.return_value = m.oci.response.Response(
        200, {}, m.oci.identity.models.BulkActionResourceTypeCollection(items=[
            m.oci.identity.models.BulkActionResourceType(name='Instance', metadata_keys=[])]),
        None)
    identity.bulk_move_resources.return_value = NS(headers={'opc-work-request-id': 'work'})

    def initialize(self, mod):
        self.module = mod
        self.client = identity

    client_factory.side_effect = [search, work_client]
    with patch.object(m.OciModuleBase, '__init__', initialize):
        helper = m.OciCompartmentMove(module)
    search.search_resources.return_value = response(resource())
    return helper


@pytest.fixture
def bucket_type():
    return m.oci.identity.models.BulkActionResourceType(
        name='Bucket', metadata_keys=['bucketName', 'namespaceName'])


@pytest.fixture
def clock(monkeypatch):
    timer = NS(now=0)

    def advance(seconds):
        timer.now += seconds

    monkeypatch.setattr(m.time, 'monotonic', lambda: timer.now)
    monkeypatch.setattr(m.time, 'sleep', advance)
    timer.advance = advance
    return timer


def work_response(status='SUCCEEDED'):
    return m.oci.response.Response(200, {}, m.oci.work_requests.models.WorkRequest(
        status=status, resources=[m.oci.work_requests.models.WorkRequestResource(
            action_type='UPDATED', entity_type='Instance', identifier='ocid1.instance.oc1.region.example')]), None)


def resource(compartment='source', kind='Instance', context=None):
    return m.oci.resource_search.models.ResourceSummary(identifier='ocid1.instance.oc1.region.example', compartment_id=compartment,
                                                        resource_type=kind, identity_context=context or {}, lifecycle_state='AVAILABLE')


def response(*resources, headers=None):
    return m.oci.response.Response(200, headers or {}, m.oci.resource_search.models.ResourceSummaryCollection(items=list(resources)), None)


def execute(helper):
    with pytest.raises(Result) as result:
        helper.execute_module()
    return result.value.data


@pytest.mark.parametrize('target', ['ocid1.compartment.oc1..target', 'ocid1.tenancy.oc1..target'])
def test_move_waits_for_search_and_routes_identity(mover, target, work_client):
    mover.module.params['target_compartment_id'] = target
    mover.search.search_resources.side_effect = [response(resource()), response(resource()), response(resource(mover.module.params['target_compartment_id']))]
    with patch.object(m.time, 'sleep'):
        result = execute(mover)
    assert result['changed'] and not result.get('failed')
    assert result['resource']['compartment_id'] == mover.module.params['target_compartment_id']
    mover.client.base_client.set_region.assert_called_once_with('home')
    work_client.base_client.set_region.assert_called_once_with('home')
    mover.search.base_client.set_region.assert_called_once_with('resource-region')
    args, kwargs = mover.client.bulk_move_resources.call_args
    assert args[1].target_compartment_id == target
    assert args[0] == 'source' and len(args[1].resources) == 1
    assert args[1].resources[0].identifier == mover.module.params['resource_id']
    assert kwargs['opc_retry_token']


@pytest.mark.parametrize('check,destination,changed', [(False, True, False), (True, True, False), (True, False, True)])
@pytest.mark.parametrize('target', ['ocid1.compartment.oc1..target', 'ocid1.tenancy.oc1..target'])
def test_no_submission(mover, check, destination, changed, target):
    mover.module.params['target_compartment_id'] = target
    mover.module.check_mode = check
    mover.search.search_resources.return_value = response(resource(mover.module.params['target_compartment_id'] if destination else 'source'))
    result = execute(mover)
    assert not result.get('failed')
    assert result['changed'] is changed
    mover.client.bulk_move_resources.assert_not_called()


def test_no_wait(mover, work_client):
    mover.module.params['wait'] = False
    assert execute(mover)['work_request_id'] == 'work'
    work_client.get_work_request.assert_not_called()
    assert mover.search.search_resources.call_count == 1


def test_unsupported_type(mover):
    mover.search.search_resources.return_value = response(resource(kind='Unsupported'))
    result = execute(mover)
    assert result['failed'] and 'does not support' in result['msg']
    mover.client.bulk_move_resources.assert_not_called()


def test_bucket_and_future_type_need_no_catalog(mover):
    mover.module.params['wait'] = False
    mover.client.list_bulk_action_resource_types.return_value.data.items = [
        m.oci.identity.models.BulkActionResourceType(name='FutureType', metadata_keys=['newKey'])]
    mover.search.search_resources.return_value = response(resource(kind='FutureType', context={'newKey': 'value'}))
    assert execute(mover)['changed']
    details = mover.client.bulk_move_resources.call_args.args[1]
    assert details.resources[0].metadata == {'newKey': 'value'}
    assert details.resources[0].entity_type == 'FutureType'


@pytest.mark.parametrize('state', ['FAILED', 'CANCELED', 'FUTURE_STATUS'])
def test_work_failure_preserves_acceptance(mover, state, work_client):
    work_client.get_work_request.return_value.data.status = state
    work_client.list_work_request_errors.return_value.data = [
        m.oci.work_requests.models.WorkRequestError(code='MoveFailed', message='Move denied')]
    result = execute(mover)
    assert result['failed'] and result['changed'] and result['work_request_id'] == 'work'
    assert 'Move denied' in result['msg']
    assert result['work_request_status'] == ('UNKNOWN_ENUM_VALUE' if state == 'FUTURE_STATUS' else state)


def test_search_timeout_is_distinct(mover, clock):
    result = execute(mover)
    assert result['failed'] and result['changed']
    assert 'OCI completed the move' in result['msg']


def test_work_timeout(mover, clock, work_client):
    work_client.get_work_request.return_value.data.status = 'IN_PROGRESS'
    result = execute(mover)
    assert result['failed'] and 'work request' in result['msg']


@pytest.mark.parametrize('value', ["ocid1.instance.oc1..x' or identifier != 'x", '', 'bucket-name'])
def test_invalid_id_never_queries(mover, value):
    mover.module.params['resource_id'] = value
    assert execute(mover)['failed']
    mover.search.search_resources.assert_not_called()


def test_missing_resource(mover):
    mover.search.search_resources.return_value = response()
    assert 'cannot find' in execute(mover)['msg']
    mover.client.bulk_move_resources.assert_not_called()


def test_pagination(mover):
    mover.module.params['wait'] = False
    mover.search.search_resources.side_effect = [response(headers={'opc-next-page': 'next'}), response(resource())]
    mover.client.list_bulk_action_resource_types.side_effect = [
        m.oci.response.Response(200, {'opc-next-page': 'next'}, m.oci.identity.models.BulkActionResourceTypeCollection(items=[]), None),
        mover.client.list_bulk_action_resource_types.return_value]
    assert execute(mover)['changed']
    assert mover.search.search_resources.call_args.kwargs['page'] == 'next'
    assert mover.client.list_bulk_action_resource_types.call_args.kwargs['page'] == 'next'


def test_principal_tenancy(mover):
    mover.client.base_client.config = {}
    mover.client.base_client.signer.tenancy_id = 'principal-tenancy'
    mover.configure_identity()
    assert mover.client.list_region_subscriptions.call_args.args == ('principal-tenancy',)


@pytest.mark.parametrize('missing', [True, False])
def test_submission_failure_and_missing_work_id(mover, missing):
    if missing:
        mover.client.bulk_move_resources.return_value.headers = {}
    else:
        mover.client.bulk_move_resources.side_effect = ValueError('Submission rejected')
    result = execute(mover)
    assert result['failed'] and result['changed'] is missing


def test_work_request_not_visible_then_success(mover, work_client):
    work_client.get_work_request.side_effect = [
        m.oci.exceptions.ServiceError(404, 'NotFound', {}, 'Pending'), work_client.get_work_request.return_value]
    mover.search.search_resources.side_effect = [response(resource()), response(resource(mover.module.params['target_compartment_id']))]
    with patch.object(m.time, 'sleep'):
        result = execute(mover)
    assert not result.get('failed') and result['changed']


@pytest.mark.parametrize('check', [False, True])
def test_bucket_metadata_is_discovered(mover, check, bucket_type):
    mover.module.params['wait'] = False
    mover.module.check_mode = check
    mover.client.list_bulk_action_resource_types.return_value.data.items = [
        bucket_type]
    expanded = resource(kind='Bucket')
    expanded.display_name = 'bucket'
    expanded.additional_details = {'namespace': 'namespace'}
    mover.search.search_resources.side_effect = [response(resource(kind='Bucket')), response(expanded)]
    result = execute(mover)
    assert result['changed'] and not result.get('failed')
    query = mover.search.search_resources.call_args.args[0].query
    assert 'query Bucket resources return allAdditionalFields where identifier' in query
    if check:
        mover.client.bulk_move_resources.assert_not_called()
    else:
        assert mover.client.bulk_move_resources.call_args.args[1].resources[0].metadata == {
            'bucketName': 'bucket', 'namespaceName': 'namespace'}


@pytest.mark.parametrize('mode', ['missing', 'empty', 'changed', 'not_found'])
def test_incomplete_discovery_never_submits(mover, mode, bucket_type):
    mover.client.list_bulk_action_resource_types.return_value.data.items = [
        bucket_type]
    expanded = resource(kind='Bucket', compartment='other' if mode == 'changed' else 'source')
    expanded.display_name = 'bucket'
    expanded.additional_details = {'namespace': ''} if mode == 'empty' else {}
    mover.search.search_resources.side_effect = [
        response(resource(kind='Bucket')), response() if mode == 'not_found' else response(expanded)]
    result = execute(mover)
    assert result['failed'] and not result['changed']
    mover.client.bulk_move_resources.assert_not_called()


def test_generic_identifiers_from_expanded_search(mover):
    mover.module.params['wait'] = False
    mover.client.list_bulk_action_resource_types.return_value.data.items = [
        m.oci.identity.models.BulkActionResourceType(name='FutureType', metadata_keys=['newKey'])]
    expanded = resource(kind='FutureType')
    expanded.additional_details = {'newKey': 'value'}
    mover.search.search_resources.side_effect = [response(resource(kind='FutureType')), response(expanded)]
    assert not execute(mover).get('failed')
    assert mover.client.bulk_move_resources.call_args.args[1].resources[0].metadata == {'newKey': 'value'}


def test_work_and_search_share_deadline(mover, clock, work_client):
    work_client.get_work_request.side_effect = [work_response('IN_PROGRESS'), work_client.get_work_request.return_value]
    result = execute(mover)
    assert result['failed'] and 'OCI completed the move' in result['msg']
    assert work_client.get_work_request.call_count == 2


def test_bucket_retains_identifiers_from_identity_context(mover, bucket_type):
    mover.module.params['wait'] = False
    mover.client.list_bulk_action_resource_types.return_value.data.items = [
        bucket_type]
    initial = resource(kind='Bucket', context={'namespaceName': 'namespace'})
    expanded = resource(kind='Bucket', context={'namespaceName': 'namespace'})
    expanded.display_name = 'bucket'
    mover.search.search_resources.side_effect = [response(initial), response(expanded)]
    assert not execute(mover).get('failed')
    assert mover.client.bulk_move_resources.call_args.args[1].resources[0].metadata == {
        'bucketName': 'bucket', 'namespaceName': 'namespace'}


@pytest.mark.parametrize('check', [False, True])
def test_unchanged_skips_identity_discovery(mover, check):
    mover.module.check_mode = check
    mover.search.search_resources.return_value = response(resource(mover.module.params['target_compartment_id']))
    mover.client.list_region_subscriptions.side_effect = ValueError('Unavailable')
    mover.client.list_bulk_action_resource_types.side_effect = ValueError('Unavailable')
    result = execute(mover)
    assert not result.get('failed') and not result['changed']
    assert result['resource_type'] == 'Instance'
    mover.client.list_region_subscriptions.assert_not_called()
    mover.client.list_bulk_action_resource_types.assert_not_called()
    mover.client.bulk_move_resources.assert_not_called()


@pytest.mark.parametrize('value', ['', '  ', None, 42, {}])
@pytest.mark.parametrize('source', ['identity_context', 'additional_details'])
def test_expanded_metadata_retains_valid_values(mover, bucket_type, value, source):
    mover.module.params['wait'] = False
    mover.client.list_bulk_action_resource_types.return_value.data.items = [bucket_type]
    initial = resource(kind='Bucket', context={'namespaceName': 'namespace'})
    expanded = resource(kind='Bucket')
    expanded.display_name = 'bucket'
    setattr(expanded, source, {'namespaceName': value})
    mover.search.search_resources.side_effect = [response(initial), response(expanded)]
    result = execute(mover)
    assert not result.get('failed')
    assert mover.client.bulk_move_resources.call_args.args[1].resources[0].metadata == {
        'bucketName': 'bucket', 'namespaceName': 'namespace'}


@pytest.mark.parametrize('check', [False, True])
def test_metadata_resolves_once(mover, check):
    mover.module.check_mode = check
    mover.module.params['wait'] = False
    with patch.object(mover, 'resolve_metadata', wraps=mover.resolve_metadata) as resolve:
        assert not execute(mover).get('failed')
    resolve.assert_called_once()


def test_diagnostic_failure_keeps_primary_error(mover, work_client):
    work_client.get_work_request.return_value = work_response('FAILED')
    work_client.list_work_request_errors.side_effect = ValueError('Diagnostic unavailable')
    result = execute(mover)
    assert result['failed'] and result['changed']
    assert result['work_request_id'] == 'work'
    assert result['work_request_status'] == 'FAILED'
    assert 'Bulk move failed with status FAILED' in result['msg']
    assert 'Diagnostic unavailable' in result['msg']


@pytest.mark.parametrize('target', ['ocid1.instance.oc1..target', 'ocid1.tenancyextra.oc1..target', 'root', "ocid1.tenancy.oc1..x'"])
def test_invalid_destination_never_queries(mover, target):
    mover.module.params['target_compartment_id'] = target
    assert execute(mover)['failed']
    mover.search.search_resources.assert_not_called()
    mover.client.bulk_move_resources.assert_not_called()


def test_expired_poll_never_fetches(mover, clock):
    fetch = Mock()
    with pytest.raises(TimeoutError):
        mover.poll(fetch, lambda value: True, 0, 'expired')
    fetch.assert_not_called()


def test_poll_rejects_late_success(mover, clock):
    def fetch():
        clock.advance(31)
        return True

    with pytest.raises(TimeoutError):
        mover.poll(fetch, bool, 30, 'expired')


@pytest.mark.parametrize('phase', ['work', 'search'])
def test_late_sdk_success_fails(mover, clock, phase, work_client):
    def late_response(*args, **kwargs):
        clock.advance(31)
        return work_response() if phase == 'work' else response(resource(mover.module.params['target_compartment_id']))

    if phase == 'work':
        work_client.get_work_request.side_effect = late_response
    else:
        def search(*args, **kwargs):
            if mover.search.search_resources.call_count == 1:
                return response(resource())
            return late_response()
        mover.search.search_resources.side_effect = search
    result = execute(mover)
    assert result['failed'] and result['changed']
    assert work_client.base_client.timeout == (10, 60)
    assert mover.search.base_client.timeout == (10, 60)


def test_retries_stop_at_deadline(mover, clock, work_client):
    mover.module.params['wait_interval'] = 20
    work_client.get_work_request.side_effect = m.oci.exceptions.ServiceError(503, 'Unavailable', {}, 'Retry')
    result = execute(mover)
    assert result['failed'] and result['changed']
    assert clock.now == 30
    assert work_client.get_work_request.call_count == 2
    assert isinstance(work_client.get_work_request.call_args.kwargs['retry_strategy'], m.oci.retry.NoneRetryStrategy)
    assert work_client.base_client.timeout == (10, 60)


def test_search_pages_share_deadline(mover, clock):
    def search(*args, **kwargs):
        if mover.search.search_resources.call_count == 1:
            return response(resource())
        clock.advance(15)
        return response(headers={'opc-next-page': 'next'})

    mover.search.search_resources.side_effect = search
    result = execute(mover)
    assert result['failed'] and result['changed']
    assert mover.search.search_resources.call_count == 3
    assert clock.now == 30


def test_diagnostic_retries_keep_failure(mover, clock, work_client):
    work_client.get_work_request.return_value = work_response('FAILED')
    work_client.list_work_request_errors.side_effect = m.oci.exceptions.ServiceError(503, 'Unavailable', {}, 'Retry')
    result = execute(mover)
    assert result['failed'] and result['work_request_status'] == 'FAILED'
    assert 'Bulk move failed with status FAILED' in result['msg']
    assert 'Timed out retrieving' in result['msg']
    assert clock.now == 30


def test_request_timeout_uses_remaining_budget(mover, clock, work_client):

    def fetch(*args, **kwargs):
        assert work_client.base_client.timeout == (10, 15)
        return work_response()

    work_client.get_work_request.side_effect = fetch
    mover.call_during_wait(work_client, work_client.get_work_request, 30, 'expired', 'work')
    assert work_client.base_client.timeout == (10, 60)


def test_search_retry_uses_shared_deadline(mover, clock):
    mover.search.search_resources.side_effect = [
        response(resource()),
        m.oci.exceptions.ServiceError(503, 'Unavailable', {}, 'Retry'),
        response(resource(mover.module.params['target_compartment_id'])),
    ]
    result = execute(mover)
    assert not result.get('failed') and result['changed']
    assert clock.now == 1
    assert mover.search.search_resources.call_count == 3


def test_diagnostic_pagination(mover, work_client):
    work_client.get_work_request.return_value = work_response('FAILED')
    work_client.list_work_request_errors.side_effect = [
        m.oci.response.Response(200, {'opc-next-page': 'next'}, [], None),
        m.oci.response.Response(200, {}, [
            m.oci.work_requests.models.WorkRequestError(code='Denied', message='Permission denied')], None),
    ]
    result = execute(mover)
    assert result['failed'] and 'Permission denied' in result['msg']
    assert work_client.list_work_request_errors.call_args.kwargs['page'] == 'next'


@pytest.mark.parametrize('mode', ['check', 'no_wait', 'unchanged', 'rejected'])
def test_work_client_is_unnecessary(mover, client_factory, mode):
    assert mover.work is None
    client_factory.side_effect = ValueError('Work Requests unavailable')
    if mode == 'check':
        mover.module.check_mode = True
    elif mode == 'no_wait':
        mover.module.params['wait'] = False
    elif mode == 'unchanged':
        mover.search.search_resources.return_value = response(resource(mover.module.params['target_compartment_id']))
    else:
        mover.client.bulk_move_resources.side_effect = ValueError('Submission rejected')
    result = execute(mover)
    assert bool(result.get('failed')) is (mode == 'rejected')
    assert mover.work is None
    assert client_factory.call_count == 1


def test_work_client_initializes_after_acceptance(mover, client_factory, work_client):
    assert mover.work is None

    def initialize(module, client_class):
        assert mover.result['changed']
        assert mover.result['work_request_id'] == 'work'
        assert client_class is m.oci.work_requests.WorkRequestClient
        return work_client

    client_factory.side_effect = initialize
    mover.search.search_resources.side_effect = [response(resource()), response(resource(mover.module.params['target_compartment_id']))]
    assert not execute(mover).get('failed')
    assert client_factory.call_count == 2
    work_client.base_client.set_region.assert_called_once_with('home')


def test_work_client_initialization_failure_preserves_acceptance(mover, client_factory):
    client_factory.side_effect = ValueError('Work Requests unavailable')
    result = execute(mover)
    assert result['failed'] and result['changed']
    assert result['work_request_id'] == 'work'
    assert 'Work Requests unavailable' in result['msg']


@pytest.mark.parametrize('check', [False, True])
@pytest.mark.parametrize('source', ['parameter', 'config', 'signer'])
def test_foreign_root_fails_before_discovery(mover, check, source):
    mover.module.check_mode = check
    mover.module.params['target_compartment_id'] = 'ocid1.tenancy.oc1..foreign'
    mover.client.base_client.config = {}
    mover.client.base_client.signer.tenancy_id = None
    tenancy = 'ocid1.tenancy.oc1..current'
    if source == 'parameter':
        mover.module.params['tenancy'] = tenancy
    elif source == 'config':
        mover.client.base_client.config['tenancy'] = tenancy
    else:
        mover.client.base_client.signer.tenancy_id = tenancy
    result = execute(mover)
    assert result['failed'] and not result['changed']
    assert 'must match' in result['msg']
    mover.search.search_resources.assert_not_called()
    mover.client.bulk_move_resources.assert_not_called()


def test_root_requires_resolved_tenancy(mover):
    mover.module.params['target_compartment_id'] = 'ocid1.tenancy.oc1..target'
    mover.client.base_client.config = {}
    mover.client.base_client.signer.tenancy_id = None
    result = execute(mover)
    assert result['failed'] and 'Set tenancy' in result['msg']
    mover.search.search_resources.assert_not_called()


def test_tenancy_resolution_precedence(mover):
    mover.module.params['tenancy'] = 'parameter'
    mover.client.base_client.config = {'tenancy': 'configuration'}
    mover.client.base_client.signer.tenancy_id = 'signer'
    assert mover.get_tenancy_id() == 'parameter'
    del mover.module.params['tenancy']
    assert mover.get_tenancy_id() == 'configuration'
    mover.client.base_client.config = {}
    assert mover.get_tenancy_id() == 'signer'


def test_submission_uses_one_sdk_retry_policy(mover):
    client = object.__new__(m.oci.identity.IdentityClient)
    client.base_client = Mock()
    client.base_client.get_preferred_retry_strategy.return_value = None
    client.base_client.call_api.__name__ = 'call_api'
    client.base_client.call_api.side_effect = m.oci.exceptions.ServiceError(503, 'Unavailable', {}, 'Retry')
    client.retry_strategy = None
    client.circuit_breaker_callback = None
    mover.client = client
    move_type = m.oci.identity.models.BulkActionResourceType(name='Instance', metadata_keys=[])
    with patch('oci.retry.retry.time.sleep'), pytest.raises(m.oci.exceptions.ServiceError):
        mover.submit_move(resource(), move_type, {})
    calls = client.base_client.call_api.call_args_list
    assert len(calls) == 8
    tokens = {call.kwargs['header_params']['opc-retry-token'] for call in calls}
    assert len(tokens) == 1 and next(iter(tokens))
    assert not mover.result['changed']
