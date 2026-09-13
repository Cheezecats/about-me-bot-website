import json
import pytest
from fastapi.testclient import TestClient
from backend.api import app
from backend.generation import answer
from backend.generation.navigation import catalog, navigation_reply
from backend.generation.conversation import ConversationState
from backend import config

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(answer, 'generate_answer', lambda *a, **kw: (config.REFUSAL_MESSAGE, False))
    with TestClient(app, base_url='http://localhost') as client:
        yield client

def send(client, question, session='navigation-tests'):
    response = client.post('/api/chat', json={'question':question, 'session_id':session})
    assert response.status_code == 200, response.text
    return response.json()

@pytest.mark.parametrize('question,ids', [
    ("Direct me to James's pictures", ['photography']),
    ('show his favoriate picture', ['authors-choice']),
    ('Take me to his photografy', ['photography']),
    ('Where can I see his pics?', ['photography']),
    ('Show me his videos', ['videos']),
    ('Show me his essays', ['essays']),
    ('Show me his hobbys', ['hobbies']),
    ('Where can I hear his favorite song?', ['song-youtube','song-spotify']),
    ('What about his favorite football team?', ['real-madrid','cr7-history']),
    ('Show me DECO*27', ['deco27-youtube','deco27-spotify']),
    ('Show me his favorite bands', ['yorushika-youtube','yorushika-spotify','hitorie-youtube','hitorie-spotify']),
])
def test_navigation_wording(client, question, ids):
    body = send(client, question)
    assert body['status'] == 'answered', body
    assert body['actions'] == ids, body

def test_picks_derive_count_from_actual_featured_photos(client):
    body = send(client, 'Show his favorite picture')
    count = sum(bool(p.get('featured')) for p in json.loads(config.CONTENT_EXPORT_PATH.read_text())['photos'])
    assert f'{count} curated photo picks' in body['answer']
    assert 'rather than one documented favorite' in body['answer']

def test_memory_ambiguity_reset_and_topic_changes(client):
    assert send(client, 'Take me there')['status'] == 'clarification'
    send(client, 'Show me his photos')
    assert send(client, 'Take me there')['actions'] == ['photography']
    send(client, 'Thanks!')
    assert send(client, 'Take me there')['actions'] == ['photography']
    send(client, 'What music does James like?')
    assert send(client, 'Where can I hear that song?')['actions'] == ['song-youtube','song-spotify']
    send(client, 'When did James start tennis?')
    assert send(client, 'Take me there')['actions'] == []
    assert send(client, 'Take me there', 'new-session')['status'] == 'clarification'
    send(client, 'Show me his photos and videos')
    assert send(client, 'Take me there')['status'] == 'clarification'

@pytest.mark.parametrize('question', [
    'Show me his private pictures', "Show me his father's photos", 'Show Flappy Bird pictures',
    'Show me his favorite restaurant', 'Show me his music at https://evil.example',
    'Show me his camera settings',
])
def test_no_destinations_for_unavailable_or_excluded_information(client, question):
    assert send(client, question)['actions'] == []

def test_football_evidence_does_not_claim_current_roster(client):
    body = send(client, 'What is his favorite football team?')
    assert 'Real Madrid, especially the Cristiano Ronaldo era' in body['answer']
    assert body['sources']
    assert 'currently' not in body['answer']

def test_catalog_only_contains_supported_destinations():
    from urllib.parse import urlparse
    assert len(catalog()) == len(json.loads((config.DATA_DIR/'chat_destinations.json').read_text()))
    for entry in catalog().values():
        if entry['kind'] == 'internal':
            assert entry['href'] in ['/photography','/photography#authors-choice','/videos','/essays','/hobbies']
        else:
            url = urlparse(entry['href'])
            assert url.scheme == 'https'
            assert url.hostname in {'www.youtube.com','open.spotify.com','www.realmadrid.com'}

def test_information_requests_do_not_become_navigation_commands():
    assert navigation_reply('What genres does James listen to?') is None
    assert navigation_reply('Does James watch football?') is None

def test_explicit_service_and_typed_reference(client):
    body = send(client, 'Where can I hear his favorite song on Spotify?')
    assert body['actions'] == ['song-spotify']
    send(client, 'Show me his pictures')
    assert send(client, 'Where can I hear that song?')['status'] == 'clarification'

def test_navigation_cannot_leak_previous_fact_context(client):
    send(client, 'When did James start tennis?')
    send(client, 'Show me his pictures')
    body = send(client, 'When did he start?')
    assert '2018' not in body['answer']

def test_mixed_navigation_and_fact_question_keeps_both_parts(client):
    body = send(client, 'Show me his photos and what camera does he use?')
    assert 'Nikon Z8' in body['answer']
    assert body['actions'] == ['photography']
    assert body['sources']
