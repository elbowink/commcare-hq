from django.core.management.base import BaseCommand
import sys
from corehq import Domain


class Command(BaseCommand):

    def handle(self, *args, **options):
        if len(args) != 1:
            print 'usage is ./manage.py delete_dynamic_reports report_type'
            sys.exit(1)

        report_type = args[0]
        if raw_input(
                'Really delete all reports of type {}? (y/n)\n'.format(report_type)).lower() == 'y':
            for domain in Domain.get_all():
                save_domain = False
                for report_config in domain.dynamic_reports:
                    old_report_count = len(report_config.reports)
                    report_config.reports = [r for r in report_config.reports if r.report != report_type]
                    if len(report_config.reports) != old_report_count:
                        save_domain = True
                if save_domain:
                    print 'removing reports from {}'.format(domain.name)
                    domain.save()
        else:
            print 'aborted'
