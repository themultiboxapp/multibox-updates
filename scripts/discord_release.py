"""Announce a version increase; manual runs never post. Standard library only."""
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?', value):
        raise ValueError('Expected a stable version such as 3.1.5 or 3.1.5.1')
    parts = tuple(map(int, value.split('.')))
    return parts + (0,) * (4 - len(parts))


def payload(release):
    number = release['version']
    version(number)
    notes = str(release.get('notes', '')).strip()[:3200]
    return {
        'username': 'Multi Box Updates',
        'allowed_mentions': {'parse': []},
        'embeds': [{
            'title': f'Multi Box {number} is available',
            'url': 'https://multibox-app.com',
            'color': 0x8950EF,
            'description': notes or 'A new Multi Box release is available.',
            'fields': [
                {'name': 'Already purchased?', 'value': '[Open your Gumroad library](https://app.gumroad.com/library) and select Multi Box.'},
                {'name': 'Purchased without an account?', 'value': 'Open your original Gumroad receipt email and choose **View content**. No account is needed. [Download help](https://gumroad.com/help/article/199-how-do-i-access-my-purchase)'},
                {'name': 'Install the update', 'value': 'Back up your settings, download the latest setup and run it. Questions? Visit the server’s help-and-faq channel.'},
            ],
            'footer': {'text': 'Multi Box • Gaming, trading and everyday workflows'},
        }],
    }


def main():
    current = json.loads(Path('updates.json').read_text())['stable']
    message = payload(current)
    if os.getenv('GITHUB_EVENT_NAME') != 'push':
        print('PREVIEW ONLY — no Discord message sent.')
        print(json.dumps(message, indent=2))
        return
    if int(os.getenv('GITHUB_RUN_ATTEMPT', '1')) != 1:
        raise ValueError('Rerun blocked to avoid a duplicate announcement. Check Discord before retrying manually.')
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    before = event.get('before', '')
    if not re.fullmatch(r'[0-9a-f]{40}', before) or before == '0' * 40:
        print('No previous release to compare; initial setup does not announce.')
        return
    old_json = subprocess.check_output(['git', 'show', before + ':updates.json'], text=True)
    old = json.loads(old_json)['stable']
    if version(current['version']) <= version(old['version']):
        print('Version unchanged or lower; no announcement sent.')
        return
    webhook = os.environ.get('DISCORD_WEBHOOK_URL', '')
    if not re.fullmatch(r'https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_.-]+', webhook):
        raise ValueError('Set the DISCORD_WEBHOOK_URL repository secret to the announcement channel webhook.')
    request = urllib.request.Request(webhook + '?wait=true', data=json.dumps(message).encode(),
                                     headers={'Content-Type': 'application/json', 'User-Agent': 'MultiBox-Release-Notifier/1.0'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            sent = json.load(response)
            if not sent.get('id'):
                raise ValueError('Discord did not confirm a message ID.')
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError('Discord delivery failed or is uncertain. Check the channel before retrying. Webhook details omitted.') from None
    print('Discord confirmed the release announcement.')


if __name__ == '__main__':
    main()
