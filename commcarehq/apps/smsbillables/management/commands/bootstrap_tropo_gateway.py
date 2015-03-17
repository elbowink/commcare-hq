import logging
from django.core.management.base import LabelCommand

from commcarehq.apps.accounting.models import Currency
from commcarehq.apps.tropo.api import TropoBackend
from commcarehq.apps.sms.models import INCOMING, OUTGOING
from commcarehq.apps.smsbillables.models import SmsGatewayFee, SmsGatewayFeeCriteria

logger = logging.getLogger('accounting')


def bootstrap_tropo_gateway(orm):
    currency = (orm['accounting.Currency'] if orm else Currency).objects.get(code="USD")
    sms_gateway_fee_class = orm['smsbillables.SmsGatewayFee'] if orm else SmsGatewayFee
    sms_gateway_fee_criteria_class = orm['smsbillables.SmsGatewayFeeCriteria'] if orm else SmsGatewayFeeCriteria

    SmsGatewayFee.create_new(
        TropoBackend.get_api_id(),
        INCOMING,
        0.01,
        currency=currency,
        fee_class=sms_gateway_fee_class,
        criteria_class=sms_gateway_fee_criteria_class,
    )

    rates_csv = open('commcarehq/apps/smsbillables/management/'
                     'pricing_data/tropo_international_rates_2013-12-19.csv', 'r')
    for line in rates_csv.readlines():
        data = line.split(',')
        if data[1] == 'Fixed Line' and data[4] != '\n':
            SmsGatewayFee.create_new(
                TropoBackend.get_api_id(),
                OUTGOING,
                float(data[4].rstrip()),
                country_code=int(data[2]),
                currency=currency,
                fee_class=sms_gateway_fee_class,
                criteria_class=sms_gateway_fee_criteria_class,
            )
    rates_csv.close()

    # Fee for invalid phonenumber
    SmsGatewayFee.create_new(
        TropoBackend.get_api_id(), OUTGOING, 0.01,
        country_code=None,
        currency=currency,
        fee_class=sms_gateway_fee_class,
        criteria_class=sms_gateway_fee_criteria_class,
    )

    logger.info("Updated Tropo gateway fees.")

class Command(LabelCommand):
    help = "bootstrap Tropo gateway fees"
    args = ""
    label = ""

    def handle(self, *args, **options):
        bootstrap_tropo_gateway(None)