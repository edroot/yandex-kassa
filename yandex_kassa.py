# coding: utf-8

import logging
import datetime
from hashlib import md5
from urllib.parse import parse_qs

from django.conf import settings
from django.http import HttpResponse

logger = logging.getLogger('logs')


class YandexKassa:
    fields = []

    def __init__(self, body):
        self.raw_body = body
        self.cleaning_data = {}
        self.shop_id = getattr(settings, 'YANDEX_KASSA_SHOP_ID', None)
        self.sc_id = getattr(settings, 'YANDEX_KASSA_SHOP_SC_ID', None)
        self.shop_password = getattr(
            settings, 'YANDEX_KASSA_SHOP_PASSWORD', None)

        logger.info('receive data (RAW): %s', self.raw_body)

        raw = parse_qs(self.raw_body)

        for key, value in raw.items():
            # delete: \\\n
            self.cleaning_data[key] = value[0].strip().strip('\\').strip()

    def _gen_md5(self, order_sum):
        """
        Генерация MD5 суммы пришедших от Yandex параметров, как указано в
        документации:

            action;orderSumAmount;orderSumCurrencyPaycash;orderSumBankPaycash;shopId;invoiceId;customerNumber;shopPassword

        :return: bool
        """

        md5_fields = [
            self.cleaning_data['action'],
            order_sum,
            self.cleaning_data['orderSumCurrencyPaycash'],
            self.cleaning_data['orderSumBankPaycash'],
            self.shop_id,
            self.cleaning_data['invoiceId'],
            self.cleaning_data['customerNumber'],
            self.shop_password
        ]

        md5_str = ';'.join(map(str, md5_fields))
        md5_sum = md5(md5_str.encode()).hexdigest().upper()

        logger.info('my MD5 sum: %s (%s)', md5_sum, md5_str)
        logger.info('receive MD5: %s', self.cleaning_data['md5'])

        if md5_sum == self.cleaning_data['md5']:
            logger.info('the MD5 order and the MD5 yandex is equal')
            return True
        else:
            logger.warning('the MD5 order and the MD5 yandex is not equal')
            return False

    def check_md5(self, order_sum):
        return self._gen_md5(order_sum)

    def check_action(self):
        raise NotImplementedError()

    def check_shop(self):
        """
        Проверка тому ли магазину пришел запрос.

        :return: bool
        """
        if self.shop_id == self.cleaning_data['shopId']:
            if self.sc_id == self.cleaning_data['scid']:
                return True

        logger.info('unknown shop IDs')
        return False

    def full_clean(self):
        fields = [
            # ['requestDatetime', ''],
            ['action', str],
            ['md5', str],
            ['shopId', int],
            ['shopArticleId', int],
            ['invoiceId', int],
            ['orderNumber', str],
            ['scid', int],
            ['customerNumber', str],
            # ['orderCreatedDatetime', ''],
            # Decimal
            ['orderSumAmount', str],
            ['orderSumCurrencyPaycash', int],
            ['orderSumBankPaycash', int],
            # Decimal
            ['shopSumAmount', str],
            ['shopSumCurrencyPaycash', int],
            ['shopSumBankPaycash', int],
            ['paymentPayerCode', int],
            ['paymentType', str],
        ]

        for item in fields:
            try:
                self.cleaning_data[item[0]] = item[1](
                    self.cleaning_data[item[0]])
            except KeyError:
                continue

        logger.info('clean data: %s', self.cleaning_data)

    def get_xml(self, code, message=None):
        if code == 0:
            xml = '<?xml version="1.0" encoding="UTF-8"?><checkOrderResponse' \
                ' performedDatetime="{date}" code="{return_code}"' \
                ' invoiceId="{invoice_id}" shopId="{shop_id}" />'.format(
                    date=datetime.datetime.now().isoformat(),
                    return_code=code,
                    invoice_id=self.cleaning_data['invoiceId'],
                    shop_id=self.cleaning_data['shopId'])
        elif code == 1:
            xml = '<?xml version="1.0" encoding="UTF-8"?><checkOrderResponse' \
                  ' performedDatetime="{date}" code="{return_code}"' \
                  ' message="{message}" />'.format(
                    date=datetime.datetime.now().isoformat(),
                    return_code=code,
                    message=message or 'MD5 not matched')
        elif code == 100:
            fields = {
                'date': datetime.datetime.now().isoformat(),
                'return_code': code,
                'message': 'unknown error'
            }
            xml = '<?xml version="1.0" encoding="UTF-8"?><checkOrderResponse' \
                  ' performedDatetime="{date}" code="{return_code}"' \
                  ' message="{message}" />'.format(**fields)
        elif code == 200:
            xml = '<?xml version="1.0" encoding="UTF-8"?><checkOrderResponse' \
                  ' performedDatetime="{date}" code="{return_code}"' \
                  ' message="{message}" />'.format(
                    date=datetime.datetime.now().isoformat(),
                    return_code=code,
                    message='unknown error')
        else:
            xml = '<?xml version="1.0" encoding="UTF-8"?><checkOrderResponse' \
                  ' performedDatetime="{date}" code="{return_code}"' \
                  ' message="{message}" />'.format(
                    date=datetime.datetime.now().isoformat(),
                    return_code=code,
                    message='unknown error')

        return xml

    def get_customer_number(self):
        """ Идентификатор плательщика на стороне магазина """
        return self.cleaning_data['customerNumber']

    def response(self, code):
        return HttpResponse(self.get_xml(code), content_type='application/xml')


class CheckOrder(YandexKassa):
    """
    https://tech.yandex.ru/money/doc/payment-solution/payment-notifications/payment-notifications-check-docpage/
    """

    def __init__(self, *args, **kwargs):
        super(CheckOrder, self).__init__(*args, **kwargs)

        self.full_clean()

    def check_action(self):
        return self.cleaning_data['action'] == 'checkOrder'

    def get_order_sum(self):
        """ Сумма заказа """
        return self.cleaning_data['orderSumAmount']

    def get_shop_sum(self):
        """ Сумма выплачиваемая магазину с вычетом комиссии Yandex """
        return self.cleaning_data['shopSumAmount']


class PaymentAviso(YandexKassa):
    """
    https://tech.yandex.ru/money/doc/payment-solution/payment-notifications/payment-notifications-aviso-docpage/
    """

    def __init__(self, *args, **kwargs):
        super(PaymentAviso, self).__init__(*args, **kwargs)

        self.full_clean()

    def check_action(self):
        return self.cleaning_data['action'] == 'paymentAviso'


class Client(YandexKassa):
    def __init__(self, *args, **kwargs):
        super(Client, self).__init__(*args, **kwargs)
        self.url = 'https://penelope-demo.yamoney.ru:8083'
