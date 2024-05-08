# -*- coding: utf-8 -*-
import datetime
from unittest import TestCase

from tests.meta_recogonize_v3 import test_name
from tests.meta_recogonize_v3.cases import testcase1
from tests.meta_recogonize_v3.cases import testcase2


class MetaV3Test(TestCase):
    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    def test_metainfo(self):
        starttime = datetime.datetime.now()
        for index, case in enumerate(testcase1.cases):
            result = test_name.parseMovie(testcase1.match, case)
            self.assertEqual(result, testcase1.cases_result[index], msg=f'Case Fail: {case}')

        starttime = datetime.datetime.now()
        for index, case in enumerate(testcase2.cases):
            result = test_name.parseMovie(testcase2.match, case)
            self.assertEqual(result, testcase2.cases_result[index], msg=f'Case Fail: {case}')

        print(f'duration: {datetime.datetime.now() - starttime}')
