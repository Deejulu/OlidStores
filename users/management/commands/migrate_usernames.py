from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import secrets
import re
import logging

from users.username_utils import ACCOUNT_ID_ALPHABET

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate existing usernames to new Olid format. Super Admins are skipped.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print changes without saving'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        all_users = User.objects.all()
        self.stdout.write(f'Total users in database: {all_users.count()}')

        migrated = []
        skipped_superadmin = []
        skipped_other = []

        for user in all_users:
            old_username = user.username

            # Skip super admins (is_superuser=True)
            if user.is_superuser:
                skipped_superadmin.append({
                    'id': user.pk,
                    'username': old_username,
                    'reason': 'Super Admin account - left untouched'
                })
                self.stdout.write(
                    self.style.WARNING(
                        f'SKIPPED (Super Admin): {old_username} (ID: {user.pk})'
                    )
                )
                continue

            # Skip users who already have Olid-format usernames
            if 'OLID' in (user.username or '') and len(user.username) > 10:
                skipped_other.append({
                    'id': user.pk,
                    'username': old_username,
                    'reason': 'Already in Olid format'
                })
                self.stdout.write(
                    f'SKIPPED (already Olid): {old_username}'
                )
                continue

            # Generate new Olid-format username
            first = re.sub(r'[^a-zA-Z]', '', user.first_name) or 'User'
            last = re.sub(r'[^a-zA-Z]', '', user.last_name) or 'Name'
            year = user.date_joined.year if user.date_joined else 2026

            # Ensure unique account_id
            if user.account_id:
                account_id = user.account_id
            else:
                account_id = ''.join(secrets.choice(ACCOUNT_ID_ALPHABET) for _ in range(4))
                while User.objects.filter(username__icontains=account_id).exclude(pk=user.pk).exists():
                    account_id = ''.join(secrets.choice(ACCOUNT_ID_ALPHABET) for _ in range(4))

            # Generate new username with Olid prefix
            random_id = ''.join(secrets.choice(ACCOUNT_ID_ALPHABET) for _ in range(4))
            new_username = f"{first}{last}{year}OLID{random_id}"

            # Ensure uniqueness
            attempts = 0
            while User.objects.filter(username__iexact=new_username).exclude(pk=user.pk).exists():
                random_id = ''.join(secrets.choice(ACCOUNT_ID_ALPHABET) for _ in range(4))
                new_username = f"{first}{last}{year}OLID{random_id}"
                attempts += 1
                if attempts > 100:
                    raise RuntimeError(f"Cannot generate unique username for {old_username}")

            if dry_run:
                self.stdout.write(
                    f'DRY RUN: {old_username} -> {new_username}'
                )
            else:
                user.username = new_username
                if not user.account_id:
                    user.account_id = account_id
                user.save(update_fields=['username', 'account_id'])
                self.stdout.write(
                    self.style.SUCCESS(f'Migrated: {old_username} -> {new_username}')
                )

            migrated.append({
                'id': user.pk,
                'old_username': old_username,
                'new_username': new_username,
                'account_id': account_id,
                'role': user.role,
            })

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('MIGRATION SUMMARY')
        self.stdout.write('=' * 50)
        self.stdout.write(f'Total users: {all_users.count()}')
        self.stdout.write(self.style.SUCCESS(f'Migrated: {len(migrated)}'))
        self.stdout.write(self.style.WARNING(f'Skipped (Super Admin): {len(skipped_superadmin)}'))
        self.stdout.write(f'Skipped (other): {len(skipped_other)}')

        if skipped_superadmin:
            self.stdout.write('\nSkipped Super Admin accounts:')
            for sa in skipped_superadmin:
                self.stdout.write(f'  - {sa["username"]} (ID: {sa["id"]}): {sa["reason"]}')

        if skipped_other:
            self.stdout.write('\nOther skipped accounts:')
            for so in skipped_other:
                self.stdout.write(f'  - {so["username"]} (ID: {so["id"]}): {so["reason"]}')

        self.stdout.write(
            self.style.SUCCESS(f'\nProcessed {len(migrated) + len(skipped_superadmin) + len(skipped_other)} accounts')
        )
