import sys
from optparse import make_option

from django.core.management import call_command
from django.core.management.base import BaseCommand

from django.utils import six


class Command(BaseCommand):
    help = 'Clears the search index of its contents.'

    option_list = BaseCommand.option_list + (
        make_option('--noinput',
            action='store_false',
            dest='interactive',
            default=True,
            help='If provided, no prompts will be issued to the user and the data will be wiped out'),
       )

    def handle(self, **options):
        if options.get('interactive', True):
            print("WARNING: This will irreparably remove EVERYTHING from your search index.")
            print("Your choices after this are to restore from backups or rebuild via the `rebuild_index` command.")

            yes_or_no = six.moves.input("Are you sure you wish to continue? [y/N] ")
            print

            if not yes_or_no.lower().startswith('y'):
                print("No action taken.")
                sys.exit()

        call_command('search_index', action='delete', confirmed='guilty-as-charged', **options)
        call_command('search_index', action='create', **options)
