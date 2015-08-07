from optparse import make_option
import sys

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
        make_option('--guilty-as-charged',
            action='store_true',
            dest='confirmed',
            default=False,
            help='Flag needed to confirm the clear index.'),
       )

    def handle(self, **options):
        if options.get('interactive', True):
            print('WARNING: This will irreparably remove EVERYTHING from your search index.')
            print('Your choices after this are to restore from backups or rebuild via the `rebuild_index` command.')

            yes_or_no = six.moves.input('Are you sure you wish to continue? [y/N] ')
            print

            if yes_or_no not in ['y', 'N']:
                print('No action taken: please type either "y" or "N".')
                sys.exit()

            if yes_or_no == 'N':
                print('No action taken.')
                sys.exit()

            if not options['confirmed']:
                print('No action taken: you must provide the --guilty-as-charged flag.')
                sys.exit()

        call_command('search_index', action='delete', **options)
        call_command('search_index', action='create', **options)
