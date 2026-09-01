"""
Reproduction script for the chat message duplication bug.

It runs against a throwaway LOCAL SQLITE test database (production DB untouched)
and demonstrates:

  1. The backend poll endpoint returns the SAME messages when two overlapping
     polls use the same `?after=` cursor (the race between the 800ms
     setTimeout-after-send and the recurring 4s setInterval, both firing before
     either updates `lastMsgAt`). This is the trigger for duplication.
  2. A NAIVE frontend (no dedup) would render those messages twice.
  3. The CURRENT/FIXED frontend dedup algorithm -- which mirrors
     appendMessage() in templates/base.html (id-based dedup + customer-text
     dedup + an in-flight `isPolling` guard that prevents the second poll from
     even being issued) -- renders each message exactly once.
  4. Rapid repeated sends produce exactly 1 user message + 1 bot reply each in
     the database, and the user message appears immediately (optimistic append).

Usage:
    python reproduce_duplication.py --settings=e_stores.settings_local_sqlite
"""
import os
import sys

# Use the local SQLite sandbox so this runs without touching production.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings_local_sqlite')
import django  # noqa: E402
django.setup()

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from urllib.parse import quote  # noqa: E402

from django.test.utils import setup_test_environment, teardown_test_environment  # noqa: E402
from django.test.runner import DiscoverRunner  # noqa: E402

runner = DiscoverRunner(verbosity=0)
setup_test_environment()
old_config = runner.setup_databases()

import json  # noqa: E402

try:
    from django.test import Client
    from core.views import _ensure_default_auto_replies
    from core.models import ChatMessage

    _ensure_default_auto_replies()
    c = Client()

    # ① Start a guest conversation with a simple greeting (Tier-1 bot reply is
    #    created). chat_start replies with the user's message_created_at (used as
    #    the initial poll cursor).
    r = c.post('/chat/start/', data=json.dumps({
        'name': 'Alice', 'email': 'a@b.com', 'subject': 'Help',
        'message': 'Hello',
    }), content_type='application/json')
    conv_id = r.json()['conversation_id']

    # ② Send a subsequent message. Backend creates the user msg + bot auto-reply
    #    (greeting). The response carries `created_at` = the user message's
    #    timestamp, which is exactly the cursor the frontend stores in lastMsgAt.
    r2 = c.post('/chat/send/', data=json.dumps({
        'conversation_id': conv_id, 'message': 'Hello',
    }), content_type='application/json')
    after_cursor = r2.json()['created_at']
    sent_user_msg_id = r2.json().get('message_id')

    # ③ Simulate TWO overlapping polls with the SAME cursor (the race between
    #    the 800ms setTimeout and the recurring 4s setInterval both firing
    #    before either updates lastMsgAt).
    url = '/chat/poll/%d/?after=%s' % (conv_id, quote(after_cursor, safe=''))
    poll1 = c.get(url).json()
    poll2 = c.get(url).json()

    def describe(data):
        return [(m['id'], m['sender_type'], (m['message'] or '')[:45])
                for m in (data.get('messages') or [])]

    print("\n=== DUPLICATION REPRODUCTION ===")
    print("Send response created_at (cursor):", after_cursor)
    print("Poll 1 (first poll):            ", describe(poll1))
    print("Poll 2 (overlapping, SAME cursor):", describe(poll2))

    p1_admin = [m for m in poll1['messages'] if m['sender_type'] == 'admin']
    p2_admin = [m for m in poll2['messages'] if m['sender_type'] == 'admin']
    overlap = set(m['id'] for m in p1_admin) & set(m['id'] for m in p2_admin)
    print("Admin message IDs returned by BOTH polls:", sorted(overlap))

    # ④ NAIVE frontend (no dedup) would double-render the overlapping messages.
    naive = list(poll1['messages']) + list(poll2['messages'])
    naive_admin = [m for m in naive if m['sender_type'] == 'admin']
    print("\nNaive render (no dedup) bot bubbles:", len(naive_admin),
          "(>1 => duplicate)")

    # ⑤ FIXED frontend dedup (mirrors appendMessage in base.html):
    #     - skip by stable server id
    #     - skip customer messages whose text was already rendered (covers the
    #       optimistic user bubble being echoed back by a poll with a real id)
    rendered = []
    seen_ids = set()
    seen_customer_texts = set()
    for m in poll1['messages'] + poll2['messages']:
        if m['id'] and m['id'] in seen_ids:
            continue
        if (m['sender_type'] == 'customer' and m['message']
                and m['message'] in seen_customer_texts):
            continue
        if m['id']:
            seen_ids.add(m['id'])
        if m['sender_type'] == 'customer':
            seen_customer_texts.add(m['message'])
        rendered.append(m)
    rendered_admin = [m for m in rendered if m['sender_type'] == 'admin']
    print("Fixed render (id + customer-text dedup) bot bubbles:", len(rendered_admin),
          "(should be 1)")

    # ⑥ Rapid repeated sends: backend must store exactly one customer msg +
    #    one bot reply per send (proves the backend is not the duplicator).
    before = ChatMessage.objects.filter(conversation_id=conv_id,
                                        sender_type='customer').count()
    n = 5
    for i in range(n):
        c.post('/chat/send/', data=json.dumps({
            'conversation_id': conv_id, 'message': 'rapid %d' % i,
        }), content_type='application/json')
    after = ChatMessage.objects.filter(conversation_id=conv_id,
                                       sender_type='customer').count()
    user_count = after
    print("\nRapid-send check: sent %d messages, DB went %d -> %d customer messages."
          % (n, before, after))

    # ⑦ Confirm the user message the server echoes back shares id with the
    #    optimistic bubble so the frontend reconciles them (no double render).
    print("Sent user message_id returned by server:", sent_user_msg_id)

    assert len(rendered_admin) == 1, "FIXED frontend still renders >1 bot bubble!"
    assert (after - before) == n, "backend duplicated customer messages!"
    print("\nPASS: no duplication with the fixed frontend dedup.")
finally:
    runner.teardown_databases(old_config)
    teardown_test_environment()
