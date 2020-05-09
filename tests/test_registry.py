import pytest
from andriller import decoders


@pytest.fixture
def registry():
    return decoders.Registry()


@pytest.mark.parametrize('file_name,result', [
    ('wa.db', [decoders.WhatsAppContactsDecoder]),
    ('msgstore.db', [decoders.WhatsAppMessagesDecoder, decoders.WhatsAppCallsDecoder]),
    ('i_do_not_exist', []),
])
def test_find_decoders_by_file_name(registry, file_name, result):
    decoders_list = registry.decoders_target(file_name)
    assert set(decoders_list) == set(result)


def test_ab_links(registry):
    links = registry.get_ab_links()
    p = 'apps/com.whatsapp/db/wa.db'
    assert p in links


def test_root_links(registry):
    links = registry.get_root_links()
    p = '/data/data/com.whatsapp/databases/wa.db'
    assert p in links
