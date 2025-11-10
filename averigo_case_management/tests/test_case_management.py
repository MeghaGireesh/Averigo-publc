from odoo.tests.common import TransactionCase, BaseCase
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging
from odoo.tests import new_test_user

_logger = logging.getLogger(__name__)

class TestScheduleCase(TransactionCase):
    def setUp(cls):
        print("--------- Case Management Test Case SetUp ---------")
        super(TestScheduleCase, cls).setUp()

    def test_schedule_case(self):
        _logger.info("Test Schedule Case")
        record1 = self.env['schedule.tech.person'].create({
            'from_date': datetime(2023, 5, 15),
            'to_date': datetime(2023, 5, 16),
            'from_time': 09.00,
            'to_time': 17.00,
            'all_day_available': False,
            'only_sunday': False,
            'only_saturday': False
        })
        _logger.info(f"Record 1")
        # Attempt to create a conflicting record
        print("self.assertRaises(UserError)",self.assertRaises(UserError))
        with self.assertRaises(UserError):
            _logger.info(f"Record 1: {record1}")
            record2 = self.env['schedule.tech.person'].create({
                'from_date': datetime(2023, 5, 15),
                'to_date': datetime(2023, 5, 16),
                'from_time': 10.00,
                'to_time': 18.00,
                'all_day_available': False,
                'only_sunday': False,
                'only_saturday': False
            })
            _logger.info(f"Record 2: {record2}")
        # Attempt to create a record with all day available
        with self.assertRaises(UserError):
            record3 = self.env['schedule.tech.person'].create({
                'from_date': datetime(2023, 5, 15),
                'to_date': datetime(2023, 5, 16),
                'from_time': 09.00,
                'to_time': 17.00,
                'all_day_available': True,
                'only_sunday': False,
                'only_saturday': False
            })
            _logger.info(f"Record 3: {record3}")

        # Attempt to create a record with only Sunday available
        with self.assertRaises(UserError):
            record4 = self.env['schedule.tech.person'].create({
                'from_date': datetime(2023, 5, 15),
                'to_date': datetime(2023, 5, 16),
                'from_time': 09.00,
                'to_time': 17.00,
                'all_day_available': False,
                'only_sunday': True,
                'only_saturday': False
            })
            _logger.info(f"Record 4")

        # Attempt to create a record with only Saturday available
        with self.assertRaises(UserError):
            record5 = self.env['schedule.tech.person'].create({
                'from_date': datetime(2023, 5, 15),
                'to_date': datetime(2023, 5, 16),
                'from_time': 09.00,
                'to_time': 17.00,
                'all_day_available': False,
                'only_sunday': False,
                'only_saturday': True
            })
            _logger.info(f"Record 5")

        # Attempt to create a record with no overlap
        with self.assertRaises(UserError):
            record6 = self.env['schedule.tech.person'].create({
                'from_date': datetime(2023, 5, 20),
                'to_date': datetime(2023, 5, 21),
                'from_time': 09.00,
                'to_time': 17.00,
                'all_day_available': False,
                'only_sunday': False,
                'only_saturday': False
            })
        with self.assertRaises(UserError):
            record7 = self.env['schedule.tech.person'].create({
                'from_date': datetime(2024, 5, 15),
                'to_date': datetime(2024, 5, 16),
                'from_time': 09.00,
                'to_time': 17.00,
                'all_day_available': False,
                'only_sunday': False,
                'only_saturday': False
            })
            _logger.info(f"Record 7: {record7}")
        _logger.info(f"Test Case Successful")

    def test_conv_time_float(self):
        _logger.info("test_conv_time_float")
        # Call the function with a valid time string
        time_float = self.env['case.management'].conv_time_float("10:30")
        # Check if the result is as expected
        self.assertAlmostEqual(time_float, 10.5, places=5)

        # Call the function with another valid time string
        time_float = self.env['case.management'].conv_time_float("23:45")
        # Check if the result is as expected
        self.assertAlmostEqual(time_float, 23.75, places=5)

        # Call the function with midnight time
        time_float = self.env['case.management'].conv_time_float("00:00")
        # Check if the result is as expected
        self.assertAlmostEqual(time_float, 0.0, places=5)

        # Call the function with a time string having only minutes
        time_float = self.env['case.management'].conv_time_float("00:30")
        # Check if the result is as expected
        self.assertAlmostEqual(time_float, 0.5, places=5)
        _logger.info("Convert time float test case successful")

    def test_case_tech_person_assign(self):
        _logger.info("-------- Test Case Tech Person Assign Started --------")
        james = new_test_user(self.env, login='hel', groups='base.group_user',
                              name='Simple employee', email='ric@example.com')
        james = james.with_user(james)
        employee = self.env['hr.employee'].create({
            'name': 'James',
            'user_id': james.id,
        })
        record1 = self.env['schedule.tech.person'].create({
            'from_date': datetime.today() - timedelta(days=10),
            'to_date': datetime.today() + timedelta(days=10),
            'from_time': 08.00,
            'to_time': 23.00,
            'all_day_available': True,
            'only_sunday': False,
            'only_saturday': False,
            'employee_ids': [(4, employee.id)]
        })
        self.assertEqual(record1.employee_ids[0].id, employee.id, "Employee "
                                                                  "Different")
        partner = self.env['res.partner'].create(
            {'name': 'Richard', 'phone': '21454', 'type': 'private'})
        category = self.env['case.management.category'].create({'name': 'Test '
                                                                        'Category'})
        type = self.env['case.management.type'].create({'name': 'Test Type'})
        record1 = self.env['case.management'].create({
            'partner_id': partner.id,
            'category_id': category.id,
            'type_id': type.id,
            'case_description': 'Test Case',
        })
        self.assertEqual(record1.employee_ids[0].id if record1.employee_ids
                         else False, employee.id, "Employee Different")
        _logger.info("-------- Test Completed --------")
