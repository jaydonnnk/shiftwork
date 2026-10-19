"""Validate the delivered local module graph and exact asset records."""
import hashlib
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / 'shiftwork/client'


def verify_http_delivery(client, assets, fetch):
    for asset in sorted(assets):
        body, mime = fetch(asset)
        assert body == (client / asset).read_bytes(), 'Served asset bytes differ from source'
        if asset.endswith('.js'):
            assert mime in ('text/javascript', 'application/javascript'), 'JavaScript URL returned incorrect MIME'


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('src', 'href'):
            if key in attrs:
                self.urls.append(attrs[key])


def asset_graph(client):
    pending = [client / 'index.html', client / 'app.js']
    seen = set()
    while pending:
        source = pending.pop().resolve()
        assert source.is_relative_to(client.resolve()), 'Asset path escapes client'
        if source in seen:
            continue
        assert source.is_file(), f'Missing local module or asset: {source.name}'
        seen.add(source)
        text = source.read_text(encoding='utf-8')
        urls = []
        if source.suffix == '.html':
            parser = References()
            parser.feed(text)
            urls += parser.urls
        if source.suffix == '.js':
            urls += re.findall(r'\b(?:import|export)\s+(?:[^;]*?\s+from\s*)?[\'"]([^\'"]+)[\'"]', text)
            for argument in re.findall(r'\bimport\s*\(([^)]+)\)', text):
                literal = re.fullmatch(r'\s*([\'"])([^\'"]+)\1\s*', argument)
                assert literal, 'Computed module import is forbidden'
                urls.append(literal.group(2))
            assert all(url.startswith(('.', '/')) for url in urls), 'External or bare module import'
        if source.suffix == '.css':
            urls += [m[1] for m in re.findall(r'url\(\s*([\'"]?)([^)\'"]+)\1\s*\)', text)]
        for url in urls:
            if url.startswith(('#', 'data:')):
                continue
            assert not re.match(r'\w+:|//', url), 'External asset URL'
            assert '?' not in url, 'Computed/cache-busted asset URL'
            target = client / url.lstrip('/') if url.startswith('/') else source.parent / url
            pending.append(target)
    return {p.relative_to(client.resolve()).as_posix() for p in seen}


def verify_records(client):
    manifest = json.loads((client / 'vendor/three-r180/manifest.json').read_bytes())
    assert manifest['version'] == '0.180.0'
    assert manifest['upstream_commit'] == '0af9729d0c143a86a1d725d6e2c3ad83301f3f34'
    assert manifest['archive_integrity'] == 'sha512-o+qycAMZrh+TsE01GqWUxUIKR1AL0S8pq7zDkYOQw8GqfX8b8VoCKYUoHbhiX5j+7hr8XsuHDVU6+gkQJQKg9w=='
    assert manifest['source_url'] == 'https://registry.npmjs.org/three/-/three-0.180.0.tgz'
    assert manifest['license'] == 'MIT' and manifest['acquired_at']
    records = manifest['files']
    assert sorted(r['path'] for r in records) == ['LICENSE', 'three.core.js', 'three.module.js']
    for row in records:
        data = (client / 'vendor/three-r180' / row['path']).read_bytes()
        assert len(data) == row['bytes'], 'Vendor byte length mismatch'
        assert hashlib.sha256(data).hexdigest() == row['sha256'], 'Vendor digest mismatch'
    license_text = (client / 'vendor/three-r180/LICENSE').read_text()
    assert 'MIT License' in license_text and 'Copyright' in license_text
    assert 'vendor/three-r180/LICENSE' in (client / 'THIRD_PARTY_NOTICES.md').read_text()
    assets = json.loads((client / 'workplace-assets.json').read_bytes())
    assert len({r['asset_id'] for r in assets}) == len(assets), 'Duplicate asset identity'
    declared = set()
    for row in assets:
        assert row['origin'] in ('shiftwork-original', 'shiftwork-existing')
        assert row['author'] and row['license'] == 'MIT' and row['external_inputs'] == []
        target = (client / row['source_path']).resolve()
        assert target.is_relative_to(client.resolve()), 'Provenance path escape'
        assert hashlib.sha256(target.read_bytes()).hexdigest() == row['source_sha256'], 'Original asset digest mismatch'
        declared.add(row['source_path'])
    graph = asset_graph(client)
    assert graph == declared | {'vendor/three-r180/three.module.js', 'vendor/three-r180/three.core.js'}, 'Undeclared asset in runtime graph'
    assert sum(r['bytes'] for r in records if r['path'].endswith('.js')) <= 3 * 1024**2
    assert sum((client / name).stat().st_size for name in graph if name.startswith('workplace-') and name.endswith('.js')) <= 180*1024
    return graph


def test_local_asset_graph_is_closed():
    assert (CLIENT / 'workplace-assets.json').is_file(), 'Original asset provenance is missing'
    verify_records(CLIENT)


@pytest.mark.parametrize('fault', [None, 'mime', 'bytes'])
def test_http_delivery_fault_controls(fault):
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.mount('/', StaticFiles(directory=CLIENT, html=True))
    with TestClient(app) as client:
        def fetch(asset):
            response = client.get('/' + asset)
            assert response.status_code == 200
            body = response.content + b'corrupt' if fault == 'bytes' else response.content
            mime = 'text/html' if fault == 'mime' else response.headers['content-type'].split(';')[0]
            return body, mime
        if fault:
            message = 'incorrect MIME' if fault == 'mime' else 'bytes differ'
            with pytest.raises(AssertionError, match=message):
                verify_http_delivery(CLIENT, {'app.js'}, fetch)
        else:
            verify_http_delivery(CLIENT, asset_graph(CLIENT), fetch)


@pytest.mark.parametrize('fault,message', [
    ('missing_core', 'Missing local module or asset'),
    ('computed', 'Computed module import'),
    ('external', 'External or bare module import'),
    ('vendor_bytes', 'Vendor byte length mismatch'),
    ('provenance', 'Original asset digest mismatch'),
])
def test_asset_faults_are_rejected(tmp_path, fault, message):
    client = tmp_path / 'client'
    shutil.copytree(CLIENT, client)
    if fault == 'missing_core':
        (client / 'vendor/three-r180/three.core.js').unlink()
        with pytest.raises(AssertionError, match=message):
            asset_graph(client)
        return
    target = client / ('app.js' if fault in ('computed', 'external') else 'vendor/three-r180/three.core.js' if fault == 'vendor_bytes' else 'workplace-rooms.js')
    suffix = '\nimport(path);\n' if fault == 'computed' else '\nimport "https://example.invalid/module.js";\n' if fault == 'external' else '\n// corrupted bytes\n'
    with target.open('ab') as stream:
        stream.write(suffix.encode())
    with pytest.raises(AssertionError, match=message):
        asset_graph(client) if fault in ('computed', 'external') else verify_records(client)
