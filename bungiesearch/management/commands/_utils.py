

def add_arguments(obj, parser):
    parser.add_argument(
        '--noinput',
        action='store_false',
        dest='interactive',
        default=True,
        help='If provided, no prompts will be issued to the user and the data will be wiped out'
    )
    parser.add_argument(
        '--guilty-as-charged',
        action='store_true',
        dest='confirmed',
        default=False,
        help='Flag needed to confirm the clear index.'
    )
    parser.add_argument(
        '--timeout',
        action='store',
        dest='timeout',
        default=None,
        type=int,
        help='Specify the timeout in seconds for each operation.'
    )
